"""Google Routes and Thermal Comfort Route Tool using PlacesServiceInterface."""

from typing import Any, Dict
from app.agent.tools.base import BaseTool
from app.services.places_service import get_places_service


class RoutesTool(BaseTool):
    """Tool to calculate transit travel time and evaluate shade/underground path coverage."""

    name = "compute_route"
    description = (
        "調用 Google Routes API 計算出發地至活動地點之大眾運輸與步行路徑。"
        "評估捷運地下街、林蔭步道遮蔽比例與熱舒適度，提供最防曬的路線指引。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "origin_lat": {
                "type": "number",
                "description": "出發地緯度 (例如使用者目前位置 25.0330)",
            },
            "origin_lng": {
                "type": "number",
                "description": "出發地經度 (例如 121.5654)",
            },
            "destination_lat": {
                "type": "number",
                "description": "目的地緯度",
            },
            "destination_lng": {
                "type": "number",
                "description": "目的地經度",
            },
            "destination_name": {
                "type": "string",
                "description": "目的地名稱，例如 'POPOP Taipei 瓶蓋工廠'",
                "default": "目的地",
            },
            "prioritize_shade": {
                "type": "boolean",
                "description": "是否優先推薦地下街與遮蔭路徑",
                "default": True,
            },
            "preference": {
                "type": "string",
                "enum": ["fastest", "wheelchair", "more_bus", "more_subway", "less_walking", "more_shading", "less_crowded", "mixed"],
                "description": "路線偏好：fastest(最快), wheelchair(無障礙/推車/大件行李), more_bus(公車+), more_subway(捷運+), less_walking(少走點), more_shading(避曬), less_crowded(避人潮), mixed(混合模式)",
                "default": "fastest",
            },
            "wheelchair_accessible": {
                "type": "boolean",
                "description": "是否需要全程無障礙電梯與低地板車輛",
                "default": False,
            },
        },
        "required": ["origin_lat", "origin_lng", "destination_lat", "destination_lng"],
    }

    async def execute(
        self,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
        destination_name: str = "目的地",
        prioritize_shade: bool = True,
        preference: str = "fastest",
        wheelchair_accessible: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute route calculation."""
        service = get_places_service()
        route = await service.compute_route(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=destination_lat,
            dest_lng=destination_lng,
            dest_name=destination_name,
            prioritize_shade=prioritize_shade,
            preference=preference,
            wheelchair_accessible=wheelchair_accessible,
        )
        return {
            "status": "success",
            "destination": route.destination,
            "preference": route.preference,
            "total_duration_minutes": route.total_duration_minutes,
            "total_distance_meters": route.total_distance_meters,
            "transit_summary": route.transit_summary,
            "underground_or_shaded_percentage": route.underground_or_shaded_percentage,
            "comfort_score": route.comfort_score,
            "route_advice": route.route_advice,
            "accessibility_note": route.accessibility_note,
            "crowd_note": route.crowd_note,
            "multimodal": route.multimodal.model_dump() if route.multimodal else None,
            "segments": [s.model_dump() for s in route.segments],
        }
