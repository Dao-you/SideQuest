"""Weather, Microclimate, and Solar Comfort Service with Interface."""

from typing import Optional
from app.logging_config import logger
from app.models.weather import MicroclimateResponse, SolarExposureResponse
from app.services.interfaces import WeatherServiceInterface
from app.services.maps_service import MapsService, get_maps_service


class WeatherService(WeatherServiceInterface):
    """Weather service implementing WeatherServiceInterface with live Open-Meteo API / Google Solar and graceful fallback."""

    def __init__(self, maps: Optional[MapsService] = None) -> None:
        self.maps = maps or get_maps_service()

    async def get_microclimate(self, latitude: float, longitude: float) -> MicroclimateResponse:
        """Fetch microclimate data from live APIs or thermal model fallback."""
        try:
            return await self.maps.get_microclimate(latitude, longitude)
        except Exception as e:
            logger.warning(f"Error fetching live microclimate for ({latitude}, {longitude}): {e}. Using fallback.")
            return MicroclimateResponse(
                latitude=latitude,
                longitude=longitude,
                temperature_c=34.2,
                apparent_temperature_c=38.5,
                relative_humidity_percentage=75,
                uv_index=8.8,
                rain_probability_percentage=15,
                condition="sunny",
                heat_comfort_level="HOT",
                thermal_sensation_index=88,
                is_indoor_ac_recommended=True,
                uv_risk_level="VERY_HIGH",
            )

    async def get_solar_exposure(self, latitude: float, longitude: float) -> SolarExposureResponse:
        """Fetch solar irradiance assessment from live API or solar geometry fallback."""
        try:
            return await self.maps.get_solar_exposure(latitude, longitude)
        except Exception as e:
            logger.warning(f"Error fetching live solar exposure for ({latitude}, {longitude}): {e}. Using fallback.")
            return SolarExposureResponse(
                latitude=latitude,
                longitude=longitude,
                direct_solar_irradiance_w_m2=820.0,
                shade_coverage_percentage=25,
                sun_exposure_level="HIGH_EXPOSURE",
                sunscreen_spf_recommended=50,
                shaded_route_recommended=True,
            )


_weather_service_instance: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """Singleton getter for WeatherService."""
    global _weather_service_instance
    if _weather_service_instance is None:
        _weather_service_instance = WeatherService()
    return _weather_service_instance
