"""Events Management and Discovery Routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_firestore_dep
from app.models.event import Event, EventCategory, EventFilter
from app.services.firestore_service import FirestoreService

router = APIRouter(prefix="/events", tags=["Events"])


@router.get(
    "",
    response_model=List[Event],
    summary="查詢活動清單",
    description="檢索台北市當期活動，支援分類、行政區、關鍵字、冷氣與室內篩選。",
)
async def list_events(
    category: Optional[str] = Query(None, description="活動分類 (art, cafe, craft, tech, music, etc.)"),
    district: Optional[str] = Query(None, description="台北市行政區"),
    is_indoor: Optional[bool] = Query(None, description="是否為室內活動"),
    ac_available: Optional[bool] = Query(None, description="是否具備冷氣空調"),
    keyword: Optional[str] = Query(None, description="關鍵字搜尋"),
    limit: int = Query(20, ge=1, le=100, description="單次查詢最大筆數"),
    offset: int = Query(0, ge=0, description="分頁位移量"),
    db: FirestoreService = Depends(get_firestore_dep),
) -> List[Event]:
    """Retrieve filtered list of events."""
    filter_params = EventFilter(
        category=category,
        district=district,
        is_indoor=is_indoor,
        ac_available=ac_available,
        keyword=keyword,
        limit=limit,
        offset=offset,
    )
    return await db.get_events(filter_params)


@router.get(
    "/categories",
    response_model=List[str],
    summary="取得所有活動分類清單",
)
async def list_categories() -> List[str]:
    """Return all supported event categories."""
    return [c.value for c in EventCategory]


@router.get(
    "/{event_id}",
    response_model=Event,
    summary="取得單一活動詳細資訊",
)
async def get_event(
    event_id: str,
    db: FirestoreService = Depends(get_firestore_dep),
) -> Event:
    """Retrieve event by unique ID."""
    event = await db.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event with ID '{event_id}' not found.")
    return event
