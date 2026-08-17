"""Weather, Microclimate, and Solar API Routes using WeatherServiceInterface."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_weather_service_dep
from app.models.weather import MicroclimateResponse, SolarExposureResponse
from app.services.interfaces import WeatherServiceInterface

router = APIRouter(prefix="/weather", tags=["Microclimate & Solar"])


@router.get(
    "/current",
    response_model=MicroclimateResponse,
    summary="取得微氣候與紫外線指數",
    description="傳入經緯度，查詢該地點當前之微氣候、體感溫度、紫外線強度與防暑建議。",
)
async def get_current_weather(
    lat: float = Query(25.0330, description="緯度"),
    lng: float = Query(121.5654, description="經度"),
    weather_service: WeatherServiceInterface = Depends(get_weather_service_dep),
) -> MicroclimateResponse:
    """Retrieve microclimate readings for coordinates."""
    return await weather_service.get_microclimate(lat, lng)


@router.get(
    "/solar",
    response_model=SolarExposureResponse,
    summary="取得 Google Solar 日照與遮蔽分析",
    description="傳入經緯度，評估日照輻射量、遮蔽度與防曬防護指南。",
)
async def get_solar(
    lat: float = Query(25.0330, description="緯度"),
    lng: float = Query(121.5654, description="經度"),
    weather_service: WeatherServiceInterface = Depends(get_weather_service_dep),
) -> SolarExposureResponse:
    """Retrieve solar exposure analysis for coordinates."""
    return await weather_service.get_solar_exposure(lat, lng)
