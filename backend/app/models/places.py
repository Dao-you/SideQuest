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


class ShadeTimePeriod(str, Enum):
    """Preset demo scenarios used for deterministic shade estimates."""

    MORNING = "morning"
    NOON = "noon"
    EVENING = "evening"


class RoutePreference(str, Enum):
    """Supported route preference strategies."""
    FASTEST = "fastest"                # 經典/最快速
    WHEELCHAIR = "wheelchair"          # 無障礙/推車/大行李友善
    MORE_BUS = "more_bus"              # 公車優先
    MORE_SUBWAY = "more_subway"        # 軌道/捷運優先
    LESS_WALKING = "less_walking"      # 少走點/少轉乘
    MORE_SHADING = "more_shading"      # 遮陽避曬/地下街優先
    LESS_CROWDED = "less_crowded"      # 避開擁擠人潮
    MIXED = "mixed"                    # 混合交通模式


class MultimodalSummary(BaseModel):
    """Multimodal transit comparison estimates (Walk, Bike, Taxi, Transit)."""
    walk_calories: int = Field(default=0, description="Estimated calories burned walking (kcal)")
    walk_duration_minutes: int = Field(default=0, description="Estimated walking duration in minutes")
    walk_distance_meters: int = Field(default=0, description="Estimated walking distance in meters")
    bike_calories: int = Field(default=0, description="Estimated calories burned cycling (kcal)")
    bike_duration_minutes: int = Field(default=0, description="Estimated cycling duration in minutes")
    bike_cost_twd: int = Field(default=20, description="Estimated YouBike rental fee in TWD")
    bike_station: str = Field(default="YouBike 2.0 鄰近租賃站", description="Recommended bike rental station")
    taxi_duration_minutes: int = Field(default=0, description="Estimated taxi/rideshare duration in minutes")
    taxi_cost_twd: int = Field(default=0, description="Estimated taxi/Uber fare in TWD")
    transit_duration_minutes: int = Field(default=0, description="Estimated public transit duration in minutes")


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
    mode: str = Field(..., description="SUBWAY | BUS | WALK | UNDERGROUND_WALK | BICYCLE | TAXI")
    instruction: str = Field(..., description="Navigation step summary")
    duration_minutes: int
    distance_meters: int
    is_shaded_or_underground: bool = Field(default=False, description="True if sheltered from direct sun/rain")
    is_accessible: bool = Field(default=True, description="True if wheelchair, stroller, or luggage accessible")
    transit_line: Optional[str] = Field(default=None, description="Bus number or MRT line name if transit")
    crowd_level: Optional[str] = Field(default=None, description="Comfort crowd status: 舒適 | 普通 | 擁擠")


class RouteComfort(BaseModel):
    """Route calculation result with thermal comfort and preference assessment."""
    origin: str
    destination: str
    preference: str = Field(default="fastest", description="Applied route preference")
    total_duration_minutes: int
    total_distance_meters: int
    transit_summary: str
    underground_or_shaded_percentage: int = Field(..., ge=0, le=100, description="% of walk protected from sun")
    comfort_score: float = Field(..., ge=0.0, le=100.0, description="Transit comfort rating")
    route_advice: str
    sun_exposure_minutes: float = Field(default=0.0, description="Estimated direct sun exposure duration in minutes")
    shaded_distance_meters: Optional[int] = Field(default=None, description="Total protected distance in meters")
    shade_time_period: ShadeTimePeriod = Field(
        default=ShadeTimePeriod.MORNING,
        description="Hardcoded demo shade scenario: morning | noon | evening",
    )
    accessibility_note: Optional[str] = Field(default=None, description="Wheelchair / stroller / luggage notes")
    crowd_note: Optional[str] = Field(default=None, description="Crowd dispersal advice for this route")
    multimodal: Optional[MultimodalSummary] = Field(default=None, description="Multi-modal travel comparisons")
    segments: List[RouteSegment] = Field(default_factory=list)
    encoded_polyline: Optional[str] = Field(default=None, description="Google Polyline encoded path string")


class RouteComputeRequest(BaseModel):
    """Request payload for route calculation."""
    origin_lat: float = Field(..., description="Origin latitude")
    origin_lng: float = Field(..., description="Origin longitude")
    destination_lat: float = Field(..., description="Destination latitude")
    destination_lng: float = Field(..., description="Destination longitude")
    destination_name: Optional[str] = Field(default=None, description="Name of destination place")
    travel_mode: TravelMode = Field(default=TravelMode.TRANSIT, description="Base travel mode")
    prioritize_shade: bool = Field(default=True, description="Prioritize underground/shaded walkways")
    shade_time_period: ShadeTimePeriod = Field(
        default=ShadeTimePeriod.MORNING,
        description="驗收用固定遮蔭時段：morning（09:00）、noon（12:30）、evening（17:30）",
    )
    preference: RoutePreference = Field(default=RoutePreference.FASTEST, description="Routing preference strategy")
    wheelchair_accessible: bool = Field(default=False, description="Require step-free / wheelchair accessibility")
    departure_time: Optional[str] = Field(default=None, description="Optional ISO departure time or 'now'")
