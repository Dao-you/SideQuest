"""Events Management and Discovery Routes using EventServiceInterface."""

from datetime import date, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_event_service_dep
from app.models.event import Event, EventFilter
from app.services.interfaces import EventServiceInterface

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
    start_date: Optional[date] = Query(None, description="指定活動日期（台北時區，與活動日期區間有交集即可）"),
    end_date: Optional[date] = Query(None, description="指定活動結束日期（台北時區）"),
    start_time: Optional[time] = Query(None, description="指定當日開始時間（台北時區）"),
    end_time: Optional[time] = Query(None, description="指定當日結束時間（台北時區）"),
    limit: int = Query(20, ge=1, le=100, description="單次查詢最大筆數"),
    offset: int = Query(0, ge=0, description="分頁位移量"),
    event_service: EventServiceInterface = Depends(get_event_service_dep),
) -> List[Event]:
    """Retrieve filtered list of events."""
    filter_params = EventFilter(
        category=category,
        district=district,
        is_indoor=is_indoor,
        ac_available=ac_available,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    return await event_service.get_events(filter_params)


@router.get(
    "/categories",
    response_model=List[str],
    summary="取得所有活動分類清單",
)
async def list_categories(
    event_service: EventServiceInterface = Depends(get_event_service_dep),
) -> List[str]:
    """Return all supported event categories."""
    return await event_service.get_categories()


@router.get(
    "/{event_id}",
    response_model=Event,
    summary="取得單一活動詳細資訊",
)
async def get_event(
    event_id: str,
    event_service: EventServiceInterface = Depends(get_event_service_dep),
) -> Event:
    """Retrieve event by unique ID."""
    event = await event_service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"活動 ID '{event_id}' 不存在。")
    return event
