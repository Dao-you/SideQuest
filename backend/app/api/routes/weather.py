"""Weather, Microclimate, and Solar API Routes."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_maps_dep
from app.models.weather import MicroclimateResponse, SolarExposureResponse
from app.services.maps_service import MapsService

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
    district: str = Query("Taipei", description="行政區名稱"),
    maps_service: MapsService = Depends(get_maps_dep),
) -> MicroclimateResponse:
    """Retrieve microclimate readings for coordinates."""
    return await maps_service.get_microclimate(lat, lng, district)


@router.get(
    "/solar",
    response_model=SolarExposureResponse,
    summary="取得 Google Solar 日照與遮蔽分析",
    description="傳入經緯度，評估日照輻射量、遮蔽度與防曬防護指南。",
)
async def get_solar(
    lat: float = Query(25.0330, description="緯度"),
    lng: float = Query(121.5654, description="經度"),
    maps_service: MapsService = Depends(get_maps_dep),
) -> SolarExposureResponse:
    """Retrieve solar exposure analysis for coordinates."""
    return await maps_service.get_solar_exposure(lat, lng)
