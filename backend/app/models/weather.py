"""Weather, Microclimate, and Solar models."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class WeatherCondition(str, Enum):
    """Weather condition categories."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    HOT_SUN = "hot_sun"


class UVRiskLevel(str, Enum):
    """UV Risk Categories based on WHO UV Index."""
    LOW = "LOW"             # 0 - 2
    MODERATE = "MODERATE"   # 3 - 5
    HIGH = "HIGH"           # 6 - 7
    VERY_HIGH = "VERY_HIGH" # 8 - 10
    EXTREME = "EXTREME"     # 11+


class MicroclimateResponse(BaseModel):
    """Real-time microclimate and environmental reading."""
    latitude: float
    longitude: float
    district: str = "Taipei"
    temperature_c: float = Field(..., description="Air temperature in Celsius")
    apparent_temperature_c: float = Field(..., description="Feels-like temperature in Celsius")
    humidity_percentage: int = Field(..., ge=0, le=100, description="Relative humidity %")
    rain_probability_percentage: int = Field(..., ge=0, le=100, description="Precipitation probability %")
    uv_index: float = Field(..., ge=0.0, description="UV Index")
    uv_risk_level: UVRiskLevel = Field(..., description="UV Risk Assessment")
    condition: WeatherCondition = Field(default=WeatherCondition.CLEAR)
    comfort_description: str = Field(..., description="Human-readable microclimate advice")
    solar_radiation_w_m2: Optional[float] = Field(default=None, description="Global solar irradiance W/m²")
    indoor_recommended: bool = Field(default=False, description="Whether indoor activities are strongly advised")


class GoogleSolarBuildingInsights(BaseModel):
    """Google Maps Platform Solar API Building Insights."""
    name: Optional[str] = Field(default=None, description="Google Solar Building Resource Name")
    imagery_quality: str = Field(default="BASE", description="Data Quality Tier: BASE | MEDIUM | HIGH")
    imagery_date: Optional[str] = Field(default=None, description="Satellite / Aerial capture date")
    max_sunshine_hours_per_year: float = Field(default=0.0, description="Max annual sunshine hours")
    carbon_offset_factor_kg_per_mwh: float = Field(default=500.0, description="Carbon offset potential")
    building_roof_area_m2: float = Field(default=0.0, description="Usable rooftop area in m²")
    ground_area_m2: float = Field(default=0.0, description="Building ground footprint in m²")
    max_array_panels_count: int = Field(default=0, description="Max solar panel installation capacity")
    solar_potential_rating: str = Field(default="OPTIMAL", description="Solar energy and direct sun exposure classification")


class GoogleSolarDataLayers(BaseModel):
    """Google Maps Platform Solar API High-Resolution GeoTIFF Data Layers."""
    imagery_quality: str = Field(default="BASE", description="Data Quality Tier: BASE | MEDIUM | HIGH")
    imagery_date: Optional[str] = Field(default=None, description="Imagery capture date")
    dsm_url: Optional[str] = Field(default=None, description="3D Digital Surface Model (DSM) GeoTIFF URL")
    rgb_url: Optional[str] = Field(default=None, description="High-resolution aerial/satellite visual GeoTIFF URL")
    mask_url: Optional[str] = Field(default=None, description="Building rooftop mask GeoTIFF URL")
    annual_flux_url: Optional[str] = Field(default=None, description="Annual solar radiation flux map GeoTIFF URL")
    monthly_flux_url: Optional[str] = Field(default=None, description="Monthly solar radiation flux map GeoTIFF URL")
    hourly_shade_urls: list[str] = Field(default_factory=list, description="12 monthly hourly shadow and shade GeoTIFF URLs")
    is_available: bool = Field(default=True, description="Whether Google Solar Data Layers are accessible for coordinate")


class SolarExposureResponse(BaseModel):
    """Solar irradiance and shade coverage analysis."""
    latitude: float
    longitude: float
    solar_radiation_w_m2: float = Field(..., description="Global horizontal irradiance W/m²")
    shade_coverage_percentage: int = Field(..., ge=0, le=100, description="Estimated canopy / structure shade %")
    sun_exposure_level: str = Field(..., description="LOW | MODERATE | HIGH | EXTREME")
    sunscreen_recommendation: str = Field(..., description="Actionable sun safety advice")
    best_transit_mode: str = Field(default="transit_underground", description="Optimal route preference for sun avoidance")
    google_solar_available: bool = Field(default=False, description="Whether Google Solar API data is active for this location")
    google_building_insights: Optional[GoogleSolarBuildingInsights] = Field(default=None, description="Google Solar rooftop and 3D insights")
    google_data_layers: Optional[GoogleSolarDataLayers] = Field(default=None, description="Google Solar GeoTIFF raster layers (DSM & Hourly Shade)")

