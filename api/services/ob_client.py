"""
Officiële Bekendmakingen SRU client.

Endpoint: https://repository.overheid.nl/sru

Working CQL index confirmed: c.product-area=officielepublicaties
The server does not reliably support sortKeys or dcterms.issued filtering,
so we sort results client-side by dc:date after fetching.
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

_NS = {
    "sru": "http://docs.oasis-open.org/ns/search-ws/sruResponse",
    "gzd": "http://standaarden.overheid.nl/sru",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "overheidop": "http://standaarden.overheid.nl/op/terms/",
    "overheidwetgeving": "http://standaarden.overheid.nl/wetgeving/",
}

PUBLICATION_TYPES = [
    "Staatsblad",
    "Staatscourant",
    "Tractatenblad",
    "Kamerstuk",
    "Blad gemeenschappelijke regeling",
]


def _cache_key(q: str | None, pub_types: list[str], skip: int, top: int) -> str:
    raw = f"ob5|{q}|{sorted(pub_types)}|{skip}|{top}"
    return "ob:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _build_cql(q: str | None, pub_types: list[str]) -> str:
    parts: list[str] = ["c.product-area=officielepublicaties"]
    if q and q.strip():
        safe = q.strip().replace('"', '\\"')
        parts.append(f'cql.textAndIndexes="{safe}"')
    if pub_types:
        type_clauses = " OR ".join(
            f'overheidop.publicatietype="{t}"' for t in pub_types
        )
        parts.append(f"({type_clauses})")
    return " AND ".join(parts)


def _find_text(el: ET.Element, *paths: str) -> str | None:
    for path in paths:
        node = el.find(path, _NS)
        if node is not None and node.text:
            return node.text.strip()
    return None


def _parse_record(record_el: ET.Element) -> dict | None:
    original = record_el.find(".//gzd:originalData", _NS)
    search_el = original if original is not None else record_el

    title = _find_text(search_el, ".//dc:title", ".//dcterms:title")
    identifier = _find_text(search_el, ".//dc:identifier", ".//dcterms:identifier")
    date = _find_text(search_el, ".//dc:date", ".//dcterms:date", ".//dcterms:issued")
    pub_type = _find_text(search_el, ".//overheidop:publicatietype")
    description = _find_text(search_el, ".//dc:description", ".//dcterms:abstract")

    if not title and not identifier:
        return None

    url: str | None = None
    if identifier and identifier.startswith("http"):
        url = identifier
    elif identifier:
        url = f"https://zoek.officielebekendmakingen.nl/{identifier}.html"

    return {
        "id": identifier,
        "title": title or "(geen titel)",
        "type": pub_type,
        "number": None,
        "date": date,
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

    # Fetch more than requested so client-side sort gives a useful top-N.
    # For paginated requests beyond page 1 we fetch exactly what was asked.
    fetch_top = top * 3 if skip == 0 else top

    params = {
        "operation": "searchRetrieve",
        "version": "2.0",
        "maximumRecords": str(fetch_top),
        "startRecord": str(skip + 1),
        "query": _build_cql(q, pub_types),
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
    except ET.ParseError as exc:
        logger.error("OB SRU XML parse error: %s", exc)
        raise ValueError(f"Invalid XML from OB SRU: {exc}") from exc

    total_node = root.find("sru:numberOfRecords", _NS)
    total = int(total_node.text) if total_node is not None and total_node.text else None

    records_node = root.find("sru:records", _NS)
    items: list[dict] = []
    if records_node is not None:
        for record_el in records_node.findall("sru:record", _NS):
            data_el = record_el.find("sru:recordData", _NS)
            if data_el is None:
                continue
            parsed = _parse_record(data_el)
            if parsed:
                items.append(parsed)

    # Sort by date descending client-side (newest first).
    # Records with no date sort to the end.
    items.sort(key=lambda x: x.get("date") or "", reverse=True)

    # Trim to requested page size after sorting
    items = items[:top]

    logger.info("OB SRU total: %s, parsed: %d", total, len(items))
    result: dict[str, Any] = {"items": items, "total": total, "skip": skip, "top": top}
    await cache_set(cache_key, result, settings.cache_ttl_tk)
    return result
