import uuid
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import SavedSearch

router = APIRouter(prefix="/api/searches", tags=["searches"])

SESSION_COOKIE = "dashboard_session"


# ── Schemas ──────────────────────────────────────────────────────────────────


class SearchQuery(BaseModel):
    q: str | None = None
    types: list[str] = Field(default_factory=list)


class SaveSearchRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    query: SearchQuery


class SavedSearchResponse(BaseModel):
    id: str
    label: str
    query: dict[str, Any]
    created_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_or_create_session(
    response: Response,
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> str:
    if session_id and len(session_id) == 36:
        return session_id
    new_id = str(uuid.uuid4())
    response.set_cookie(
        key=SESSION_COOKIE,
        value=new_id,
        max_age=60 * 60 * 24 * 365,  # 1 year
        httponly=True,
        samesite="lax",
    )
    return new_id


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=list[SavedSearchResponse])
async def list_searches(
    session_id: str = Depends(_get_or_create_session),
    db: AsyncSession = Depends(get_db),
):
    """List saved searches for the current anonymous session."""
    result = await db.execute(
        select(SavedSearch)
        .where(SavedSearch.session_id == session_id)
        .order_by(SavedSearch.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        SavedSearchResponse(
            id=str(r.id),
            label=r.label,
            query=r.query,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.post("", response_model=SavedSearchResponse, status_code=201)
async def create_search(
    body: SaveSearchRequest,
    session_id: str = Depends(_get_or_create_session),
    db: AsyncSession = Depends(get_db),
):
    """Save a new search query for the current session."""
    row = SavedSearch(
        session_id=session_id,
        label=body.label,
        query=body.query.model_dump(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return SavedSearchResponse(
        id=str(row.id),
        label=row.label,
        query=row.query,
        created_at=row.created_at.isoformat(),
    )


@router.delete("/{search_id}", status_code=204)
async def delete_search(
    search_id: str,
    session_id: str = Depends(_get_or_create_session),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved search (only if it belongs to the current session)."""
    try:
        uid = uuid.UUID(search_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid search ID")

    result = await db.execute(
        delete(SavedSearch).where(
            SavedSearch.id == uid,
            SavedSearch.session_id == session_id,
        )
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Search not found")
