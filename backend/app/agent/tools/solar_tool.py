"""Google Solar Exposure and Shading Tool."""

from typing import Any, Dict
from app.agent.tools.base import BaseTool
from app.services.maps_service import get_maps_service


class SolarTool(BaseTool):
    """Tool to estimate solar exposure, shade coverage, and sun protection guidelines."""

    name = "get_solar_exposure"
    description = (
        "調用 Google Solar API 評估目標地點的日照輻射強度 (W/m²)、建築與行道樹陰影遮蔽率，提供避暑防曬防護指南。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "緯度座標 (例如 25.0441)",
            },
            "longitude": {
                "type": "number",
                "description": "經度座標 (例如 121.5294)",
            },
        },
        "required": ["latitude", "longitude"],
    }

    async def execute(
        self,
        latitude: float,
        longitude: float,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute solar exposure evaluation."""
        service = get_maps_service()
        solar = await service.get_solar_exposure(latitude, longitude)
        return {
            "status": "success",
            "solar_radiation_w_m2": solar.solar_radiation_w_m2,
            "shade_coverage_percentage": solar.shade_coverage_percentage,
            "sun_exposure_level": solar.sun_exposure_level,
            "sunscreen_recommendation": solar.sunscreen_recommendation,
            "best_transit_mode": solar.best_transit_mode,
        }
