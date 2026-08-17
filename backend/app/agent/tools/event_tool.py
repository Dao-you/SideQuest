"""Event Search Tool using EventServiceInterface."""

from typing import Any, Dict, Optional
from app.agent.tools.base import BaseTool
from app.models.event import EventFilter
from app.services.event_service import get_event_service


class EventTool(BaseTool):
    """Tool to search events from EventService by category, keywords, AC, and district."""

    name = "search_events"
    description = (
        "搜尋台北市當期週末展覽、藝文市集、工作坊、特色咖啡與休閒活動。"
        "支援依照類別 (art, cafe, craft, tech, music, food, outdoor, family)、關鍵字、室內冷氣 (is_indoor, ac_available) 與行政區篩選。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "活動類別 (例如 'art', 'cafe', 'craft', 'tech', 'music', 'food', 'outdoor', 'family')",
            },
            "keyword": {
                "type": "string",
                "description": "搜尋關鍵字，例如 '手作', '咖啡', '冷氣', '動漫', '展覽', '音樂'",
            },
            "district": {
                "type": "string",
                "description": "台北市行政區，例如 '中正區', '信義區', '大安區', '南港區', '中山區', '士林區'",
            },
            "is_indoor": {
                "type": "boolean",
                "description": "是否限定室內活動（炎熱或下雨時強烈建議設為 true）",
            },
            "ac_available": {
                "type": "boolean",
                "description": "是否具備冷氣空調設施",
            },
            "start_date": {
                "type": "string",
                "format": "date",
                "description": "指定活動開始日期（YYYY-MM-DD，台北時區）",
            },
            "end_date": {
                "type": "string",
                "format": "date",
                "description": "指定活動結束日期（YYYY-MM-DD，台北時區）",
            },
            "start_time": {
                "type": "string",
                "format": "time",
                "description": "指定當日開始時間（HH:MM，台北時區）",
            },
            "end_time": {
                "type": "string",
                "format": "time",
                "description": "指定當日結束時間（HH:MM，台北時區）",
            },
            "limit": {
                "type": "integer",
                "description": "回傳最大筆數 (預設 8 筆)",
                "default": 8,
            },
        },
    }

    async def execute(
        self,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        district: Optional[str] = None,
        is_indoor: Optional[bool] = None,
        ac_available: Optional[bool] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 8,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute event search query."""
        service = get_event_service()
        filter_params = EventFilter(
            category=category,
            keyword=keyword,
            district=district,
            is_indoor=is_indoor,
            ac_available=ac_available,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        events = await service.get_events(filter_params)

        results = []
        for e in events:
            results.append({
                "id": e.id,
                "title": e.title,
                "category": e.category.value,
                "venue_name": e.venue_name,
                "venue_id": e.venue_id,
                "district": e.location.district,
                "is_indoor": e.is_indoor,
                "ac_available": e.ac_available,
                "rating": e.rating,
                "price_type": e.price_type,
                "price_amount": e.price_amount,
                "tags": e.tags,
                "latitude": e.location.latitude,
                "longitude": e.location.longitude,
                "mrt_station": e.location.mrt_station,
                "description": e.description[:120] + "..." if len(e.description) > 120 else e.description,
                "start_time": e.start_time,
                "end_time": e.end_time,
            })

        return {
            "status": "success",
            "total_found": len(results),
            "events": results,
        }
