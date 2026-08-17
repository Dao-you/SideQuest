"""Google Places and Google Routes Pydantic models."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class TravelMode(str, Enum):
    """Supported travel modes."""
    TRANSIT = "TRANSIT"
    WALK = "WALK"
    DRIVE = "DRIVE"
    BICYCLE = "BICYCLE"


class PlaceDetails(BaseModel):
    """Google Places API (New) details representation."""
    place_id: str
    name: str
    formatted_address: str
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[int] = None
    open_now: Optional[bool] = None
    opening_hours_text: List[str] = Field(default_factory=list)
    wheelchair_accessible: bool = True
    serves_coffee: bool = False
    good_for_children: bool = True
    photos: List[str] = Field(default_factory=list)
    google_maps_uri: Optional[str] = None


class RouteSegment(BaseModel):
    """Individual segment in a transit / walking path."""
    mode: str = Field(..., description="SUBWAY | BUS | WALK | UNDERGROUND_WALK")
    instruction: str = Field(..., description="Navigation step summary")
    duration_minutes: int
    distance_meters: int
    is_shaded_or_underground: bool = Field(default=False, description="True if sheltered from direct sun/rain")


class RouteComfort(BaseModel):
    """Route calculation result with thermal comfort assessment."""
    origin: str
    destination: str
    total_duration_minutes: int
    total_distance_meters: int
    transit_summary: str
    underground_or_shaded_percentage: int = Field(..., ge=0, le=100, description="% of walk protected from sun")
    comfort_score: float = Field(..., ge=0.0, le=100.0, description="Transit comfort rating")
    route_advice: str
    segments: List[RouteSegment] = Field(default_factory=list)


class RouteComputeRequest(BaseModel):
    """Request payload for route calculation."""
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    destination_name: Optional[str] = None
    travel_mode: TravelMode = TravelMode.TRANSIT
    prioritize_shade: bool = True
