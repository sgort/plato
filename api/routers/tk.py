from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from services.tk_client import DOCUMENT_TYPES, fetch_tk_feed

router = APIRouter(prefix="/api/tk", tags=["tk"])


@router.get("/feed")
async def get_feed(
    q: Annotated[
        str | None, Query(description="Full-text search on document title")
    ] = None,
    types: Annotated[
        list[str] | None,
        Query(description="Filter by document type (repeatable)"),
    ] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    top: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """
    Paginated parliamentary feed from the Tweede Kamer OData API.

    - **q**: keyword filter on document title
    - **types**: one or more Soort values (Motie, Kamervraag, Brief, …)
    - **skip** / **top**: pagination
    """
    # Validate requested types against known values
    if types:
        unknown = [t for t in types if t not in DOCUMENT_TYPES]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown document type(s): {unknown}. Valid: {DOCUMENT_TYPES}",
            )

    try:
        return await fetch_tk_feed(q=q, types=types, skip=skip, top=top)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"TK API unavailable: {exc}"
        ) from exc


@router.get("/types")
async def get_document_types():
    """List of valid document type filter values."""
    return {"types": DOCUMENT_TYPES}
