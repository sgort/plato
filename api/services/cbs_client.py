"""
CBS (Statistics Netherlands) OData v4 client.

Base URL (updated 2024): https://datasets.cbs.nl/odata/v1/CBS
Old URL (opendata.cbs.nl/OData4) is decommissioned.

Datasets with multiple dimensions (e.g. TypeWoning, Goederengroep) need a
default_measure to pin a single series for the sparkline chart. Without it,
$orderby=Perioden desc returns rows interleaved across all dimension values,
making period deduplication skip most recent periods.
"""

import logging
from typing import Any

import httpx

from config import settings
from services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

_CBS_BASE = "https://datasets.cbs.nl/odata/v1/CBS"
_HTTP_TIMEOUT = 20.0

# default_measure pins a single Measure value for datasets that have extra
# dimensions, ensuring the chart shows one clean time series.
# Find valid measure codes at: {_CBS_BASE}/{code}/MeasureCodes
DATASETS: dict[str, dict[str, str]] = {
    "83474NED": {
        "label": "Bevolking — kerncijfers",
        "description": "Bevolkingsontwikkeling, geboorte, overlijden, migratie",
        "unit": "personen",
        # Single dimension (Perioden only) — no default_measure needed
    },
    "82816NED": {
        "label": "Woningvoorraad",
        "description": "Woningvoorraad naar type en eigendom",
        "unit": "woningen",
        # Dimensions: Perioden + TypeWoning. Pin to total stock.
        "default_measure": "T001044",
    },
    "85323NED": {
        "label": "Werkloosheid — kerncijfers",
        "description": "Werkloze beroepsbevolking (ILO-definitie)",
        "unit": "x 1 000 personen / %",
        # Pin to total unemployment rate (%)
        "default_measure": "T001137",
    },
    "83694NED": {
        "label": "Bbp — kwartaalrekeningen",
        "description": "Bruto binnenlands product, volumemutaties",
        "unit": "volumemutatie %",
    },
    "84637NED": {
        "label": "Consumentenprijzen — CPI",
        "description": "Consumentenprijsindex, alle huishoudens (2015=100)",
        "unit": "index",
        # Dimensions: Perioden + Bestedingscategorie. Pin to all-items index.
        "default_measure": "M000000",
    },
}


async def list_datasets() -> list[dict]:
    return [
        {"code": code, **{k: v for k, v in meta.items() if k != "default_measure"}}
        for code, meta in DATASETS.items()
    ]


async def fetch_observations(
    dataset_code: str,
    measure: str | None = None,
    periods: int = 16,
) -> dict[str, Any]:
    dataset_cfg = DATASETS.get(dataset_code, {})
    dataset_meta = {k: v for k, v in dataset_cfg.items() if k != "default_measure"}

    # Use caller-supplied measure, then dataset default, then None
    effective_measure = measure or dataset_cfg.get("default_measure")

    cache_key = f"cbs4:{dataset_code}:{effective_measure}:{periods}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    fetch_top = periods * 10

    for attempt, orderby in enumerate(["$orderby=Perioden desc", None]):
        qs_parts = [f"$top={fetch_top}"]
        if orderby:
            qs_parts.append(orderby)
        if effective_measure:
            safe = effective_measure.replace("'", "''")
            qs_parts.append(f"$filter=Measure eq '{safe}'")

        url = f"{_CBS_BASE}/{dataset_code}/Observations?{'&'.join(qs_parts)}"
        logger.info("CBS fetch (attempt %d): %s", attempt + 1, url)

        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT, follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            break
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400 and attempt == 0:
                logger.warning(
                    "CBS %s: $orderby=Perioden failed, retrying without", dataset_code
                )
                continue
            logger.error("CBS API %s — %s", exc.response.status_code, url)
            result: dict[str, Any] = {
                "dataset": {"code": dataset_code, **dataset_meta},
                "observations": [],
                "error": str(exc),
            }
            await cache_set(cache_key, result, 60)
            return result
        except httpx.RequestError as exc:
            logger.error("CBS network error: %s", exc)
            return {
                "dataset": {"code": dataset_code, **dataset_meta},
                "observations": [],
                "error": str(exc),
            }

    raw = data.get("value", [])
    if not raw:
        result = {"dataset": {"code": dataset_code, **dataset_meta}, "observations": []}
        await cache_set(cache_key, result, settings.cache_ttl_static)
        return result

    period_col = _detect_period_col(raw[0])
    logger.info(
        "CBS %s — period column: %s, rows: %d", dataset_code, period_col, len(raw)
    )

    by_period: dict[str, float | None] = {}
    for row in raw:
        p = str(row.get(period_col, "") or "").strip()
        if p and p not in by_period:
            by_period[p] = row.get("Value")

    sorted_periods = sorted(by_period.keys())[-periods:]
    observations = [
        {"period": p, "value": by_period[p], "measure": effective_measure or ""}
        for p in sorted_periods
    ]

    result = {
        "dataset": {"code": dataset_code, **dataset_meta},
        "observations": observations,
    }
    await cache_set(cache_key, result, settings.cache_ttl_static)
    return result


def _detect_period_col(row: dict) -> str:
    for name in ("Perioden", "perioden", "Periods", "periods"):
        if name in row:
            return name
    for key, val in row.items():
        if isinstance(val, str) and any(x in val for x in ("JJ", "KW", "MM")):
            return key
    return "Perioden"
