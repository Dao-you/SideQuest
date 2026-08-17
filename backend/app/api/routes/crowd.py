"""Crowd Density and Heatmap Layer Routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_firestore_dep
from app.models.crowd import HeatmapPoint, VenueLiveStatus
from app.services.firestore_service import FirestoreService

router = APIRouter(prefix="/crowd", tags=["Crowd Density & Heatmap"])


@router.get(
    "/heatmap",
    response_model=List[HeatmapPoint],
    summary="取得 Google Maps 熱力圖圖層座標點",
    description="提供前端 Google Maps JavaScript API HeatmapLayer 繪製即時人潮熱力圖所需之權重點位資料。",
)
async def get_heatmap(
    db: FirestoreService = Depends(get_firestore_dep),
) -> List[HeatmapPoint]:
    """Retrieve normalized heatmap points for map rendering."""
    return await db.get_heatmap_points()


@router.get(
    "/venues",
    response_model=List[VenueLiveStatus],
    summary="取得所有場館即時擁擠狀態清單",
)
async def list_venues(
    db: FirestoreService = Depends(get_firestore_dep),
) -> List[VenueLiveStatus]:
    """Retrieve all venues live status."""
    return await db.get_all_venues()


@router.get(
    "/venues/{venue_id}",
    response_model=VenueLiveStatus,
    summary="取得單一場館即時狀態",
)
async def get_venue(
    venue_id: str,
    db: FirestoreService = Depends(get_firestore_dep),
) -> VenueLiveStatus:
    """Retrieve venue live status by ID."""
    venue = await db.get_venue_by_id(venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail=f"Venue '{venue_id}' not found.")
    return venue
