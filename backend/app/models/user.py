"""User and Mock Authentication Models for PRD MVP."""

from typing import List, Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """User Profile for Mock Persona and Login."""
    user_id: str = Field(..., description="Unique user ID or session user ID")
    name: str = Field(..., description="User display name")
    email: str = Field(..., description="User email (simulated)")
    avatar_url: str = Field(default="", description="User avatar image URL")
    persona_title: str = Field(default="週末探索者", description="User persona description")
    favorite_categories: List[str] = Field(default_factory=list, description="Default interest categories")
    favorite_tags: List[str] = Field(default_factory=list, description="Preferred keyword tags")
    favorite_event_ids: List[str] = Field(default_factory=list, description="Bookmarked event IDs")
    prefer_indoor: bool = Field(default=True, description="Default indoor AC preference")
    avoid_crowd: bool = Field(default=True, description="Default crowd avoidance preference")
    max_budget: Optional[int] = Field(default=500, description="Default budget ceiling in TWD")
    is_mock_account: bool = Field(default=True, description="Identifies mock MVP account")


class MockLoginRequest(BaseModel):
    """Request to log in with a test account or guest mode."""
    account_id: Optional[str] = Field(
        default="demo_weekend_explorer",
        description="Preset account ID: 'demo_weekend_explorer', 'demo_tech_geek', 'demo_crowd_avoider', 'demo_family_parent' or custom ID",
    )
    custom_name: Optional[str] = Field(default=None, description="Custom display name for guest login")


class FavoriteToggleRequest(BaseModel):
    """Request to add or remove an event from favorites."""
    event_id: str = Field(..., description="Target event ID")


class FavoriteToggleResponse(BaseModel):
    """Response after toggling favorite status."""
    event_id: str
    is_favorited: bool
    total_favorites: int
    message: str


class UpdatePreferencesRequest(BaseModel):
    """Request to update user preferences."""
    favorite_categories: Optional[List[str]] = None
    favorite_tags: Optional[List[str]] = None
    prefer_indoor: Optional[bool] = None
    avoid_crowd: Optional[bool] = None
    max_budget: Optional[int] = None
