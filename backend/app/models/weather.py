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
    indoor_recommended: bool = Field(default=False, description="Whether indoor activities are strongly advised")


class SolarExposureResponse(BaseModel):
    """Solar irradiance and shade coverage analysis."""
    latitude: float
    longitude: float
    solar_radiation_w_m2: float = Field(..., description="Global horizontal irradiance W/m²")
    shade_coverage_percentage: int = Field(..., ge=0, le=100, description="Estimated canopy / structure shade %")
    sun_exposure_level: str = Field(..., description="LOW | MODERATE | HIGH | EXTREME")
    sunscreen_recommendation: str = Field(..., description="Actionable sun safety advice")
    best_transit_mode: str = Field(default="transit_underground", description="Optimal route preference for sun avoidance")
