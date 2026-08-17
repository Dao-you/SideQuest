"""User & Mock Persona Profile Endpoints (PRD Section 7.1)."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.event import Event
from app.models.user import (
    FavoriteToggleResponse,
    MockLoginRequest,
    UpdatePreferencesRequest,
    UserProfile,
)
from app.services.firestore_service import get_firestore_service
from app.services.user_service import get_user_service

router = APIRouter(prefix="/user", tags=["User & Persona (Mock Login)"])


@router.get("/personas", response_model=List[UserProfile], summary="取得 4 大預設測試角色清單 (PRD 4 & 7.1)")
async def list_preset_personas():
    """Returns the 4 preset test accounts for quick demo login without passwords."""
    user_service = get_user_service()
    preset_ids = ["demo_weekend_explorer", "demo_tech_geek", "demo_crowd_avoider", "demo_family_parent"]
    return [user_service.get_user_profile(uid) for uid in preset_ids]


@router.post("/mock-login", response_model=UserProfile, summary="模擬登入 (Demo Login)")
async def mock_login(req: MockLoginRequest):
    """Log in as a preset demo persona or guest without formal authentication (PRD 7.1)."""
    user_service = get_user_service()
    return user_service.mock_login(account_id=req.account_id, custom_name=req.custom_name)


@router.get("/profile", response_model=UserProfile, summary="取得使用者偏好與收藏狀態")
async def get_profile(user_id: str = Query(default="demo_weekend_explorer", description="User identifier")):
    """Get profile, interest tags, and bookmarked event IDs."""
    user_service = get_user_service()
    return user_service.get_user_profile(user_id)


@router.post("/favorites/{event_id}", response_model=FavoriteToggleResponse, summary="收藏 / 取消收藏活動")
async def toggle_favorite(
    event_id: str,
    user_id: str = Query(default="demo_weekend_explorer", description="User identifier"),
):
    """Add or remove an event from user bookmarks."""
    user_service = get_user_service()
    firestore_service = get_firestore_service()
    
    # Verify event exists
    event = await firestore_service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"活動 ID '{event_id}' 不存在")

    return user_service.toggle_favorite(user_id=user_id, event_id=event_id)


@router.get("/favorites", response_model=List[Event], summary="取得個人收藏活動清單")
async def get_favorites(user_id: str = Query(default="demo_weekend_explorer", description="User identifier")):
    """Get the full Event objects that the user has favorited."""
    user_service = get_user_service()
    firestore_service = get_firestore_service()
    user = user_service.get_user_profile(user_id)

    favorited_events: List[Event] = []
    for eid in user.favorite_event_ids:
        ev = await firestore_service.get_event_by_id(eid)
        if ev:
            favorited_events.append(ev)
    return favorited_events


@router.put("/preferences", response_model=UserProfile, summary="更新個人偏好條件")
async def update_preferences(
    req: UpdatePreferencesRequest,
    user_id: str = Query(default="demo_weekend_explorer", description="User identifier"),
):
    """Update user categories, tags, budget, and indoor/crowd preferences."""
    user_service = get_user_service()
    return user_service.update_preferences(
        user_id=user_id,
        favorite_categories=req.favorite_categories,
        favorite_tags=req.favorite_tags,
        prefer_indoor=req.prefer_indoor,
        avoid_crowd=req.avoid_crowd,
        max_budget=req.max_budget,
    )
