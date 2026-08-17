"""Google Places Details Tool using PlacesServiceInterface."""

from typing import Any, Dict, Optional
from app.agent.tools.base import BaseTool
from app.services.places_service import get_places_service


class PlacesTool(BaseTool):
    """Tool to fetch Google Places API rating, photos, business hours, and accessibility."""

    name = "get_place_details"
    description = (
        "調用 Google Places API (New) 查詢場館的地點評分、評論摘要、營業時間、無障礙設施與照片參照。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "place_name": {
                "type": "string",
                "description": "地點或場館名稱，例如 'POPOP Taipei 瓶蓋工廠', '華山1914', 'C-LAB 臺灣當代文化實驗場'",
            },
            "latitude": {
                "type": "number",
                "description": "緯度座標 (可選)",
            },
            "longitude": {
                "type": "number",
                "description": "經度座標 (可選)",
            },
        },
        "required": ["place_name"],
    }

    async def execute(
        self,
        place_name: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute Google Places query."""
        service = get_places_service()
        details = await service.get_place_details(place_name, latitude, longitude)
        return {
            "status": "success",
            "place_id": details.place_id,
            "name": details.name,
            "address": details.formatted_address,
            "rating": details.rating,
            "user_ratings_total": details.user_ratings_total,
            "open_now": details.open_now,
            "wheelchair_accessible": details.wheelchair_accessible,
            "serves_coffee": details.serves_coffee,
            "google_maps_uri": details.google_maps_uri,
        }
