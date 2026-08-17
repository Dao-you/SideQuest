"""Weather and Microclimate Tool using WeatherServiceInterface."""

from typing import Any, Dict
from app.agent.tools.base import BaseTool
from app.services.weather_service import get_weather_service


class WeatherTool(BaseTool):
    """Tool to check microclimate, temperature, and UV index."""

    name = "check_weather"
    description = (
        "查詢台北指定座標或行政區之即時氣溫、體感溫度、降雨機率與紫外線 (UV) 指數。"
        "用於評估戶外舒適度與是否需要啟動室內/遮蔭推薦。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "緯度 (例如 25.0441)",
            },
            "longitude": {
                "type": "number",
                "description": "經度 (例如 121.5294)",
            },
            "district": {
                "type": "string",
                "description": "行政區名稱，例如 '中正區', '信義區', '南港區'",
                "default": "台北市",
            },
        },
        "required": ["latitude", "longitude"],
    }

    async def execute(
        self,
        latitude: float,
        longitude: float,
        district: str = "台北市",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute microclimate check."""
        weather_service = get_weather_service()
        micro = await weather_service.get_microclimate(latitude, longitude)
        return {
            "status": "success",
            "temperature_c": micro.temperature_c,
            "apparent_temperature_c": micro.apparent_temperature_c,
            "humidity_percentage": micro.humidity_percentage,
            "rain_probability_percentage": micro.rain_probability_percentage,
            "uv_index": micro.uv_index,
            "uv_risk_level": micro.uv_risk_level.value,
            "condition": micro.condition.value,
            "indoor_recommended": micro.indoor_recommended,
            "comfort_description": micro.comfort_description,
        }
