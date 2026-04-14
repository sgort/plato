from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from services.ob_client import PUBLICATION_TYPES, fetch_ob_feed

router = APIRouter(prefix="/api/ob", tags=["ob"])


@router.get("/feed")
async def get_ob_feed(
    q: Annotated[str | None, Query()] = None,
    types: Annotated[list[str] | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    top: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """
    Paginated publication feed from Officiële Bekendmakingen (SRU).

    - **q**: full-text search on title and description
    - **types**: one or more publication types (Staatsblad, Staatscourant, …)
    """
    if types:
        unknown = [t for t in types if t not in PUBLICATION_TYPES]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown publication type(s): {unknown}. Valid: {PUBLICATION_TYPES}",
            )
    try:
        return await fetch_ob_feed(q=q, pub_types=types, skip=skip, top=top)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OB SRU unavailable: {exc}") from exc


@router.get("/types")
async def get_publication_types():
    return {"types": PUBLICATION_TYPES}
