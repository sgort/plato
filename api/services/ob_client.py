"""
Officiële Bekendmakingen SRU client.

SRU endpoint: https://zoekservice.overheid.nl/sru/Search
Connection:   officielepublicaties

Covers: Staatsblad, Staatscourant, Kamerstukken, ministerial letters, etc.
Docs:   https://zoekservice.overheid.nl/

SRU (Search/Retrieve via URL) returns Dublin Core XML.
We parse it to a flat item list compatible with the feed schema.
"""

import hashlib
import logging
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from config import settings
from services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

_SRU_BASE = "https://zoekservice.overheid.nl/sru/Search"
_HTTP_TIMEOUT = 15.0

# XML namespaces in SRU responses
_NS = {
    "srw": "http://www.loc.gov/zing/srw/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "overheidwetgeving": "http://standaarden.overheid.nl/wetgeving/",
    "overheidop": "http://standaarden.overheid.nl/op/terms/",
    "ovrext": "http://standaarden.overheid.nl/sru",
}

# Publication type labels used for filter chips in the frontend
PUBLICATION_TYPES = [
    "Staatsblad",
    "Staatscourant",
    "Tractatenblad",
    "Kamerstuk",
    "Blad gemeenschappelijke regeling",
]


def _cache_key(q: str | None, pub_types: list[str], skip: int, top: int) -> str:
    raw = f"ob|{q}|{sorted(pub_types)}|{skip}|{top}"
    return "ob:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _build_cql(q: str | None, pub_types: list[str]) -> str:
    """
    Build a CQL (Contextual Query Language) string for the SRU $filter.
    SRU uses CQL rather than OData syntax.
    """
    parts: list[str] = []

    if q and q.strip():
        safe = q.strip().replace('"', '\\"')
        parts.append(f'dcterms.title any "{safe}" or dc.description any "{safe}"')

    if pub_types:
        type_clauses = " or ".join(
            f'overheidop.publicatietype = "{t}"' for t in pub_types
        )
        parts.append(f"({type_clauses})")

    return " and ".join(parts) if parts else "dc.title any *"


def _parse_record(record_el: ET.Element) -> dict | None:
    """Parse one SRU recordData element into a normalised item dict."""
    # recordData > gzd > originalData > owms:owmskern or dc fields
    # The structure varies by publication type; we fall back gracefully.
    def find_text(el: ET.Element, *paths: str) -> str | None:
        for path in paths:
            node = el.find(path, _NS)
            if node is not None and node.text:
                return node.text.strip()
        return None

    title = find_text(record_el, ".//dc:title", ".//dcterms:title")
    identifier = find_text(record_el, ".//dc:identifier", ".//dcterms:identifier")
    date = find_text(record_el, ".//dc:date", ".//dcterms:date", ".//dcterms:modified")
    pub_type = find_text(record_el, ".//overheidop:publicatietype")
    description = find_text(record_el, ".//dc:description", ".//dcterms:abstract")

    if not title and not identifier:
        return None

    # Build a URL from the identifier if it looks like a web address
    url: str | None = None
    if identifier and identifier.startswith("http"):
        url = identifier
    elif identifier:
        url = f"https://officielebekendmakingen.nl/{identifier}"

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

    params = {
        "x-connection": "officielepublicaties",
        "operation": "searchRetrieve",
        "version": "2.0",
        "maximumRecords": top,
        "startRecord": skip + 1,  # SRU is 1-indexed
        "query": _build_cql(q, pub_types),
        "recordSchema": "http://www.loc.gov/zing/srw/",
        "sortKeys": "dcterms.modified,,0",  # most recent first
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

    # Total hits
    total_node = root.find("srw:numberOfRecords", _NS)
    total = int(total_node.text) if total_node is not None and total_node.text else None

    # Records
    records_node = root.find("srw:records", _NS)
    items: list[dict] = []
    if records_node is not None:
        for record_el in records_node.findall("srw:record", _NS):
            data_el = record_el.find("srw:recordData", _NS)
            if data_el is None:
                continue
            parsed = _parse_record(data_el)
            if parsed:
                items.append(parsed)

    result = {"items": items, "total": total, "skip": skip, "top": top}
    await cache_set(cache_key, result, settings.cache_ttl_tk)
    return result
