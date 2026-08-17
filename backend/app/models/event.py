"""Event and Recommendation Pydantic Models."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class EventCategory(str, Enum):
    """Event Categories."""
    ART = "art"
    MUSIC = "music"
    FOOD = "food"
    OUTDOOR = "outdoor"
    TECH = "tech"
    FAMILY = "family"
    CAFE = "cafe"
    CRAFT = "craft"
    EXHIBITION = "exhibition"
    MARKET = "market"
    WORKSHOP = "workshop"


class RegistrationStatus(str, Enum):
    """Event Registration / Ticket Status."""
    OPEN = "open"              # 可直接報名 / 購票
    FREE_ENTRY = "free_entry"  # 免費免報名自由入場
    WAITLIST = "waitlist"      # 候補中
    FULL = "full"              # 已額滿


class CardRole(str, Enum):
    """Recommendation Card Role in PRD Section 7.4."""
    TOP_MATCH = "TOP_MATCH"                          # 最符合需求
    DISPERSAL_ALTERNATIVE = "DISPERSAL_ALTERNATIVE"  # 替代選擇 (舒適/近/便宜)
    EXPLORATION_GEM = "EXPLORATION_GEM"              # 探索選擇 (新鮮感/特色)


class Location(BaseModel):
    """Geographical Location Model."""
    latitude: float = Field(..., description="Latitude in decimal degrees")
    longitude: float = Field(..., description="Longitude in decimal degrees")
    address: str = Field(..., description="Full postal address")
    district: str = Field(default="Taipei", description="Administrative district")
    mrt_station: Optional[str] = Field(default=None, description="Closest MRT station name")
    mrt_distance_meters: Optional[int] = Field(default=None, description="Walking distance to MRT station in meters")


class Event(BaseModel):
    """Event Schema stored in Firestore and returned by APIs."""
    id: str = Field(..., description="Unique event identifier")
    title: str = Field(..., description="Event title")
    category: EventCategory = Field(..., description="Event category")
    description: str = Field(default="", description="Detailed event summary")
    venue_name: str = Field(..., description="Venue or building name")
    venue_id: str = Field(..., description="Associated venue identifier")
    location: Location = Field(..., description="Geographical coordinate and address")
    is_indoor: bool = Field(default=True, description="Whether the event is indoors")
    ac_available: bool = Field(default=True, description="Air conditioning available")
    start_time: str = Field(..., description="ISO 8601 start timestamp")
    end_time: str = Field(..., description="ISO 8601 end timestamp")
    tags: List[str] = Field(default_factory=list, description="Keywords and topic tags")
    price_type: str = Field(default="free", description="'free' or 'paid'")
    price_amount: Optional[int] = Field(default=0, description="Admission price in TWD")
    registration_status: RegistrationStatus = Field(default=RegistrationStatus.OPEN, description="Registration status")
    source_platform: str = Field(default="官方網站", description="Original platform: Accupass, Luma, KKTIX, 台北旅遊網, etc.")
    capacity: Optional[int] = Field(default=100, description="Estimated venue capacity")
    estimated_duration_hours: float = Field(default=2.0, description="Estimated duration to spend in hours")
    rating: float = Field(default=4.5, ge=1.0, le=5.0, description="Google / User rating")
    review_count: int = Field(default=50, description="Total number of reviews")
    image_url: str = Field(default="", description="Event cover photo URL")
    source_url: str = Field(default="", description="Original ticketing or info URL")
    last_updated: Optional[str] = Field(default=None, description="ISO timestamp of last data refresh")


class DispersalBadgeType(str, Enum):
    """Badges indicating comfort, crowd status, or smart dispersal."""
    HIDDEN_GEM = "HIDDEN_GEM"
    CROWD_WARNING = "CROWD_WARNING"
    COOL_HAVEN = "COOL_HAVEN"
    SHADED_ROUTE = "SHADED_ROUTE"
    FAMILY_FRIENDLY = "FAMILY_FRIENDLY"
    TOP_MATCH = "TOP_MATCH"
    DISPERSAL_ALTERNATIVE = "DISPERSAL_ALTERNATIVE"
    EXPLORATION = "EXPLORATION"


class DispersalBadge(BaseModel):
    """Visual Badge displayed on UI Recommendation Cards."""
    type: DispersalBadgeType
    label: str
    color: str = Field(default="green", description="Badge color token (green, red, blue, orange, purple, teal)")


class RecommendationCard(BaseModel):
    """Structured Recommendation Card returned by Agent & Recommendation API."""
    event: Event
    card_role: CardRole = Field(default=CardRole.TOP_MATCH, description="TOP_MATCH | DISPERSAL_ALTERNATIVE | EXPLORATION_GEM")
    card_role_label: str = Field(default="🎯 最符合需求", description="Human-readable card badge label")
    total_score: float = Field(..., ge=0.0, le=100.0, description="Final weighted score")
    match_score: float = Field(..., ge=0.0, le=100.0, description="Interest relevance score (35% weight)")
    time_feasibility_score: float = Field(default=90.0, ge=0.0, le=100.0, description="Time feasibility score (25% weight)")
    accessibility_score: float = Field(..., ge=0.0, le=100.0, description="Transit ease and shade score (20% weight)")
    budget_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Budget feasibility score (10% weight)")
    weather_comfort_score: float = Field(..., ge=0.0, le=100.0, description="Microclimate comfort index (10% weight)")
    crowd_score: int = Field(..., ge=0, le=100, description="Live crowd congestion index")
    crowd_level: str = Field(..., description="LOW | MODERATE | HIGH | OVERLOADED")
    transit_summary: str = Field(default="", description="Brief transit & shade guide")
    recommendation_reason: str = Field(..., description="Personalized AI explanation for recommendation")
    badges: List[DispersalBadge] = Field(default_factory=list, description="Dispersal and comfort badges")
    is_dispersal_alternative: bool = Field(default=False, description="True if recommended as a low-crowd alternative")
    alternative_for_venue: Optional[str] = Field(default=None, description="Name of crowded venue this replaces")


class EventFilter(BaseModel):
    """Filter parameters for querying events."""
    category: Optional[str] = None
    district: Optional[str] = None
    is_indoor: Optional[bool] = None
    ac_available: Optional[bool] = None
    price_type: Optional[str] = None
    registration_status: Optional[str] = None
    keyword: Optional[str] = None
    min_rating: Optional[float] = None
    max_crowd: Optional[int] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
