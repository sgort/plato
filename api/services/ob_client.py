"""
Officiële Bekendmakingen SRU client.

Endpoint: https://repository.overheid.nl/sru

Namespace note: the root element uses DEFAULT namespace (no prefix):
  <searchRetrieveResponse xmlns="http://docs.oasis-open.org/ns/search-ws/sruResponse">
So ElementTree requires the full Clark notation {uri}localname for every find().

sortKeys is NOT supported — the server returns a diagnostic error when it's present.
We sort client-side by dcterms:date after fetching.
"""

import hashlib
import logging
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from config import settings
from services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

_SRU_BASE = "https://repository.overheid.nl/sru"
_HTTP_TIMEOUT = 15.0

# Clark-notation URIs for ElementTree (no prefix aliases needed)
_SRU = "http://docs.oasis-open.org/ns/search-ws/sruResponse"
_GZD = "http://standaarden.overheid.nl/sru"
_DCTERMS = "http://purl.org/dc/terms/"
_DC = "http://purl.org/dc/elements/1.1/"
_OW = "http://standaarden.overheid.nl/wetgeving/"

# Register for find() calls
_NS = {
    "sru": _SRU,
    "gzd": _GZD,
    "dcterms": _DCTERMS,
    "dc": _DC,
    "ow": _OW,
}

PUBLICATION_TYPES = [
    "Staatsblad",
    "Staatscourant",
    "Tractatenblad",
    "Kamerstuk",
    "Gemeenteblad",
    "Provinciaal blad",
    "Blad gemeenschappelijke regeling",
    "Waterschapsblad",
]


def _cache_key(q: str | None, pub_types: list[str], skip: int, top: int) -> str:
    raw = f"ob8|{q}|{sorted(pub_types)}|{skip}|{top}"
    return "ob:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _build_cql(q: str | None, pub_types: list[str]) -> str:
    parts: list[str] = [
        'c.product-area == "officielepublicaties"',
        'w.jaargang == "2026"',
    ]
    if q and q.strip():
        safe = q.strip().replace('"', '\\"')
        parts.append(f'dc.title any "{safe}" OR dc.description any "{safe}"')
    if pub_types:
        type_clauses = " OR ".join(f'w.publicatienaam == "{t}"' for t in pub_types)
        parts.append(f"({type_clauses})")
    return " AND ".join(parts)


def _text(el: ET.Element | None, tag_uri: str, tag_local: str) -> str | None:
    """Find a child by Clark notation and return its text."""
    if el is None:
        return None
    node = el.find(f"{{{tag_uri}}}{tag_local}")
    return node.text.strip() if node is not None and node.text else None


def _parse_record(record_data_el: ET.Element) -> dict | None:
    owmskern = record_data_el.find(f".//{{{_OW}}}owmskern")
    owmsmantel = record_data_el.find(f".//{{{_OW}}}owmsmantel")
    tpmeta = record_data_el.find(f".//{{{_OW}}}tpmeta")
    enriched = record_data_el.find(f".//{{{_GZD}}}enrichedData")

    if owmskern is None:
        return None

    identifier = _text(owmskern, _DCTERMS, "identifier")
    title = _text(owmskern, _DCTERMS, "title")
    date_val = _text(owmsmantel, _DCTERMS, "date")
    description = _text(owmsmantel, _DCTERMS, "abstract")
    pub_type = _text(tpmeta, _OW, "publicatienaam")

    url: str | None = None
    if enriched is not None:
        url = _text(enriched, _GZD, "preferredUrl")
    if not url and identifier:
        url = f"https://zoek.officielebekendmakingen.nl/{identifier}.html"

    if not title and not identifier:
        return None

    return {
        "id": identifier,
        "title": title or "(geen titel)",
        "type": pub_type,
        "number": None,
        "date": date_val,
        "url": url,
        "description": description,
        "source": "ob",
    }


async def fetch_ob_feed(
    q: str | None = None,
    pub_types: list[str] | None = None,
    skip: int = 0,
    top: int = 20,
) -> dict[str, Any]:
    pub_types = pub_types or []
    cache_key = _cache_key(q, pub_types, skip, top)

    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    # Fetch extra on page 1 to allow client-side sort to produce a good top-N
    fetch_top = top * 3 if skip == 0 else top

    params = {
        "operation": "searchRetrieve",
        "version": "2.0",
        "maximumRecords": str(fetch_top),
        "startRecord": str(skip + 1),
        "query": _build_cql(q, pub_types),
        # sortKeys intentionally omitted — server returns diagnostic error
    }

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(_SRU_BASE, params=params)
            response.raise_for_status()
            xml_text = response.text
    except httpx.RequestError as exc:
        logger.error("OB SRU request error: %s", exc)
        raise

    try:
        root = ET.fromstring(xml_text)
        # logger.info("OB root tag: %s", root.tag)
        # logger.info("OB root children: %s", [c.tag for c in root])
    except ET.ParseError as exc:
        logger.error("OB SRU XML parse error: %s", exc)
        raise ValueError(f"Invalid XML from OB SRU: {exc}") from exc

    # Root uses default namespace — find with Clark notation
    total_node = root.find(f"{{{_SRU}}}numberOfRecords")
    total = int(total_node.text) if total_node is not None and total_node.text else None

    records_node = root.find(f"{{{_SRU}}}records")
    items: list[dict] = []
    if records_node is not None:
        for record_el in records_node.findall(f"{{{_SRU}}}record"):
            data_el = record_el.find(f"{{{_SRU}}}recordData")
            if data_el is None:
                continue
            parsed = _parse_record(data_el)
            if parsed:
                items.append(parsed)

    # Sort newest first client-side
    items.sort(key=lambda x: x.get("date") or "", reverse=True)
    items = items[:top]

    logger.info("OB SRU total: %s, parsed: %d", total, len(items))
    result: dict[str, Any] = {"items": items, "total": total, "skip": skip, "top": top}
    await cache_set(cache_key, result, settings.cache_ttl_tk)
    return result
