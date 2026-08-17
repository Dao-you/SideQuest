"""Crowd congestion and heatmap models."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.event import Location


class CrowdLevel(str, Enum):
    """Crowd Congestion Levels."""
    LOW = "LOW"               # 0 - 35
    MODERATE = "MODERATE"     # 36 - 70
    HIGH = "HIGH"             # 71 - 85
    OVERLOADED = "OVERLOADED" # 86 - 100


class TrendDirection(str, Enum):
    """Trend of crowd flow in the next 1-2 hours."""
    RISING = "RISING"
    FALLING = "FALLING"
    STABLE = "STABLE"


class VenueLiveStatus(BaseModel):
    """Real-time crowd and venue condition status."""
    venue_id: str = Field(..., description="Unique venue identifier")
    venue_name: str = Field(..., description="Venue name")
    district: str = Field(default="Taipei", description="Administrative district")
    location: Location = Field(..., description="Venue coordinate")
    crowd_score: int = Field(..., ge=0, le=100, description="Congestion score 0-100")
    crowd_level: CrowdLevel = Field(..., description="Normalized crowd level")
    wait_time_minutes: int = Field(default=0, description="Estimated entry / service wait time")
    trend: TrendDirection = Field(default=TrendDirection.STABLE, description="Projected flow trend")
    capacity_percentage: int = Field(default=50, ge=0, le=100, description="Occupancy percentage")
    temperature_c: float = Field(default=28.0, description="Local microclimate temperature")
    uv_index: float = Field(default=5.0, description="Local UV index")
    last_updated: str = Field(..., description="ISO 8601 timestamp")


class HeatmapPoint(BaseModel):
    """Point model for rendering Google Maps JavaScript API HeatmapLayer."""
    latitude: float
    longitude: float
    weight: float = Field(..., ge=0.0, le=1.0, description="Intensity weight for heatmap")
    venue_name: str
    crowd_score: int
    crowd_level: CrowdLevel
