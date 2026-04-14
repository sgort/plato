"""
CPRMV API proxy.

Forwards rule lookups to the public CPRMV API at cprmv.open-regels.nl,
adds caching, and normalises errors.

Supported repositories:
  BWB   — Dutch national law  (e.g. BWBR0015703)
  CVDR  — Municipal/provincial regulations (e.g. CVDR712517)
  CFMX4 — EU CELLAR Formex v4

Docs: https://cprmv.open-regels.nl/docs
"""

import logging
from typing import Any

import httpx

from config import settings
from services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

_CPRMV_BASE = "https://cprmv.open-regels.nl"
_HTTP_TIMEOUT = 20.0


async def fetch_rule(rule_id_path: str, fmt: str = "cprmv-json") -> dict[str, Any] | str:
    """
    Fetch a rule from the CPRMV API.

    Args:
        rule_id_path: e.g. "BWBR0015703" or "BWBR0015703, Artikel 20"
        fmt: output format — cprmv-json (default), turtle, json-ld, n3, xml

    Returns:
        Parsed dict for cprmv-json, raw string for RDF formats.

    Raises:
        httpx.HTTPStatusError on 4xx/5xx from upstream.
        httpx.RequestError on network failure.
    """
    cache_key = f"cprmv:{rule_id_path}:{fmt}"

    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{_CPRMV_BASE}/rules/{rule_id_path}"
    params = {"format": fmt}

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("CPRMV upstream %s for %s", exc.response.status_code, rule_id_path)
        raise
    except httpx.RequestError as exc:
        logger.error("CPRMV request error: %s", exc)
        raise

    if fmt == "cprmv-json":
        result: Any = response.json()
    else:
        result = response.text

    await cache_set(cache_key, result, settings.cache_ttl_static)
    return result


async def fetch_methods() -> dict[str, Any]:
    """Return the CPRMV methods knowledge graph (supported repositories)."""
    cache_key = "cprmv:methods"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(f"{_CPRMV_BASE}/methods", params={"format": "cprmv-json"})
            response.raise_for_status()
            result = response.json()
    except Exception as exc:
        logger.error("CPRMV methods error: %s", exc)
        raise

    await cache_set(cache_key, result, settings.cache_ttl_static)
    return result
