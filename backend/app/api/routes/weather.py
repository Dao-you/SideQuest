"""Weather, Microclimate, and Solar API Routes using WeatherServiceInterface."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_weather_service_dep
from app.models.weather import (
    GoogleSolarBuildingInsights,
    GoogleSolarDataLayers,
    MicroclimateResponse,
    SolarExposureResponse,
)
from app.services.interfaces import WeatherServiceInterface
from app.services.urban_shade_service import get_urban_shade_engine

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
    description="傳入經緯度，評估日照輻射量、遮蔽度、Google Solar 建物日照潛力與防曬防護指南。",
)
async def get_solar(
    lat: float = Query(25.0330, description="緯度"),
    lng: float = Query(121.5654, description="經度"),
    weather_service: WeatherServiceInterface = Depends(get_weather_service_dep),
) -> SolarExposureResponse:
    """Retrieve solar exposure analysis for coordinates."""
    return await weather_service.get_solar_exposure(lat, lng)


@router.get(
    "/solar/building-insights",
    response_model=GoogleSolarBuildingInsights,
    summary="取得 Google Solar API 建物日照與屋頂潛力 (buildingInsights)",
    description="傳入經緯度，取得 Google Maps Platform Solar API 的建物屋頂面積、年日照時數與碳抵換量分析。",
)
async def get_google_solar_building_insights(
    lat: float = Query(25.0330, description="緯度"),
    lng: float = Query(121.5654, description="經度"),
) -> GoogleSolarBuildingInsights:
    """Retrieve Google Solar API building insights."""
    engine = get_urban_shade_engine()
    return await engine.solar_client.get_building_insights(lat, lng)


@router.get(
    "/solar/data-layers",
    response_model=GoogleSolarDataLayers,
    summary="取得 Google Solar API 高解析度 GeoTIFF 遮蔭圖層 (dataLayers)",
    description="傳入經緯度與半徑，取得 Google Solar 數位表面模型 (DSM)、12 個月每小時陰影光柵圖 (hourlyShadeUrls) 與太陽通量圖層。",
)
async def get_google_solar_data_layers(
    lat: float = Query(25.0330, description="緯度"),
    lng: float = Query(121.5654, description="經度"),
    radius_meters: int = Query(100, ge=10, le=500, description="分析半徑 (公尺)"),
) -> GoogleSolarDataLayers:
    """Retrieve Google Solar API high-resolution GeoTIFF raster layers."""
    engine = get_urban_shade_engine()
    return await engine.solar_client.get_data_layers(lat, lng, radius_meters=radius_meters)
