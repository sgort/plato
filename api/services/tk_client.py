"""
Tweede Kamer OData v4 client.

API base: https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0

Primary collection: Document
  Id               — UUID (internal, NOT used in website URLs)
  DocumentNummer   — string e.g. "2026D16594" (used in website URLs)
  Soort            — string (Motie | Amendement | Brief | Kamervraag | …)
  Onderwerp        — string (subject / title)
  GewijzigdOp      — datetime (sort field)
  Vergaderjaar     — string (e.g. "2024-2025")
  Volgnummer       — int (-1 = no value)
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
_schema_logged = False


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
    """
    Use DocumentNummer (e.g. '2026D16594') for the website URL.
    The internal UUID Id does NOT work as a TK website URL parameter.
    Confirmed URL pattern: tweedekamer.nl/kamerstukken/detail?id=2026D16594&did=2026D16594
    """
    doc_num = item.get("DocumentNummer")
    if doc_num:
        return (
            f"https://www.tweedekamer.nl/kamerstukken/detail?id={doc_num}&did={doc_num}"
        )
    return None


def _clean_number(v: Any) -> str | None:
    """Hide internal negative volgnummers (-1)."""
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
                "number": _clean_number(item.get("Volgnummer")),
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

    result: dict[str, Any] = {"items": items, "total": total, "skip": skip, "top": top}
    await cache_set(cache_key, result, settings.cache_ttl_tk)
    return result
