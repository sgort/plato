from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query
import httpx

from services.cprmv_client import fetch_methods, fetch_rule

router = APIRouter(prefix="/api/legislation", tags=["legislation"])

ValidFormat = Literal["cprmv-json", "turtle", "json-ld", "n3", "xml"]


@router.get("/rule/{rule_id_path:path}")
async def get_rule(
    rule_id_path: Annotated[
        str, Path(description="Rule path e.g. BWBR0015703 or BWBR0015703, Artikel 20")
    ],
    format: Annotated[ValidFormat, Query()] = "cprmv-json",
):
    """
    Fetch a rule from the CPRMV API (BWB, CVDR, or EU CELLAR).

    Examples:
    - `/api/legislation/rule/BWBR0015703` — full act (latest version)
    - `/api/legislation/rule/BWBR0015703, Artikel 20` — specific article
    - `/api/legislation/rule/CVDR712517` — municipal regulation
    """
    try:
        return await fetch_rule(rule_id_path, fmt=format)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502, detail=f"CPRMV API unavailable: {exc}"
        ) from exc


@router.get("/methods")
async def get_methods():
    """List supported publication methods (BWB, CVDR, CELLAR)."""
    try:
        return await fetch_methods()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
