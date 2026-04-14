from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
import httpx

from services.cbs_client import DATASETS, fetch_observations, list_datasets

router = APIRouter(prefix="/api/cbs", tags=["cbs"])


@router.get("/datasets")
async def get_datasets():
    """List available CBS datasets."""
    return {"datasets": await list_datasets()}


@router.get("/dataset/{dataset_code}/observations")
async def get_observations(
    dataset_code: Annotated[str, Path(description="CBS dataset code e.g. 83474NED")],
    measure: Annotated[
        str | None, Query(description="CBS Measure key to filter")
    ] = None,
    periods: Annotated[
        int, Query(ge=1, le=100, description="Number of most-recent periods")
    ] = 12,
):
    """
    Fetch time-series observations from a CBS dataset.

    Returns observations in chronological order (oldest first), ready for charting.
    """
    if dataset_code not in DATASETS:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_code}' not in curated list. Available: {list(DATASETS.keys())}",
        )
    try:
        return await fetch_observations(dataset_code, measure=measure, periods=periods)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502, detail=f"CBS API unavailable: {exc}"
        ) from exc
