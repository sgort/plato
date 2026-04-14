"""
Tweede Kamer OData v4 client.

API base: https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0
Documentation: https://opendata.tweedekamer.nl/documentatie/odata-api

We intentionally omit $select so the API returns all fields.
This avoids 400 errors from unknown field names and lets us log the actual
schema on the first response — check the uvicorn output to see real field names.
"""

import hashlib
import logging
import urllib.parse as _up
from typing import Any

import httpx

from config import settings
from services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

DOCUMENT_TYPES = [
    "Motie",
    "Amendement",
    "Brief",
    "Kamervraag",
    "Verslag",
    "Rapport",
    "Vergaderverslag",
    "Antwoord",
    "Besluitenlijst",
]

_HTTP_TIMEOUT = 15.0
_schema_logged = False  # log field names once on first successful response


def _build_filter(q: str | None, types: list[str]) -> str:
    parts: list[str] = ["Verwijderd eq false"]

    if q and q.strip():
        safe = q.strip().replace("'", "''")
        parts.append(f"contains(Onderwerp,'{safe}')")

    if types:
        type_clauses = " or ".join(f"Soort eq '{t}'" for t in types)
        parts.append(f"({type_clauses})")

    return " and ".join(parts)


def _build_url(q: str | None, types: list[str], skip: int, top: int) -> str:
    """
    Build the OData URL with literal $ signs.
    httpx percent-encodes $ to %24 when using params=dict, breaking OData.
    We build the query string manually to keep $ literal.
    """
    filter_str = _build_filter(q, types)
    encoded_filter = _up.quote(filter_str, safe="() =',")

    qs = (
        f"$orderby=GewijzigdOp desc"
        f"&$top={top}"
        f"&$skip={skip}"
        f"&$count=true"
        f"&$filter={encoded_filter}"
    )
    return f"{settings.tk_api_base}/Document?{qs}"


def _cache_key(q: str | None, types: list[str], skip: int, top: int) -> str:
    raw = f"tk|{q}|{sorted(types)}|{skip}|{top}"
    return "tk:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _document_url(item: dict) -> str | None:
    doc_id = item.get("Id")
    if not doc_id:
        return None
    return f"https://www.tweedekamer.nl/kamerstukken/detail?id={doc_id}"


def _clean_number(v: Any) -> str | None:
    """Hide internal negative volgnummers (-1) that have no display value."""
    if v is None:
        return None
    try:
        if int(v) < 0:
            return None
    except (TypeError, ValueError):
        pass
    return str(v)


def _normalise(raw_items: list[dict]) -> list[dict]:
    global _schema_logged
    if raw_items and not _schema_logged:
        logger.info("TK Document fields available: %s", list(raw_items[0].keys()))
        _schema_logged = True

    out = []
    for item in raw_items:
        # Be defensive — use .get() for every field so unknown names don't crash
        title = (
            item.get("Onderwerp")
            or item.get("Titel")
            or item.get("Naam")
            or "(geen onderwerp)"
        )
        date = (
            item.get("GewijzigdOp") or item.get("DatumRegistratie") or item.get("Datum")
        )
        out.append(
            {
                "id": item.get("Id"),
                "title": title,
                "type": item.get("Soort"),
                "number": _clean_number(item.get("Nummer") or item.get("Volgnummer")),
                "vergaderjaar": item.get("Vergaderjaar"),
                "date": date,
                "url": _document_url(item),
                "source": "tk",
            }
        )
    return out


async def fetch_tk_feed(
    q: str | None = None,
    types: list[str] | None = None,
    skip: int = 0,
    top: int = 20,
) -> dict[str, Any]:
    types = types or []
    cache_key = _cache_key(q, types, skip, top)

    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    url = _build_url(q, types, skip, top)
    logger.info("TK fetch: %s", url)

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("TK API %s — %s", exc.response.status_code, url)
        raise
    except httpx.RequestError as exc:
        logger.error("TK API network error: %s", exc)
        raise

    items = _normalise(data.get("value", []))
    total = data.get("@odata.count")

    result = {"items": items, "total": total, "skip": skip, "top": top}
    await cache_set(cache_key, result, settings.cache_ttl_tk)
    return result
