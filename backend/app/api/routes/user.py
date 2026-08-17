"""User & Mock Persona Profile Endpoints using UserServiceInterface (PRD Section 7.1)."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import get_user_service_dep
from app.models.event import Event
from app.models.user import (
    FavoriteToggleResponse,
    MockLoginRequest,
    UpdatePreferencesRequest,
    UserProfile,
)
from app.services.interfaces import UserServiceInterface

router = APIRouter(prefix="/user", tags=["User & Persona (Mock Login)"])


@router.get(
    "/personas",
    response_model=List[UserProfile],
    summary="取得 4 大預設測試角色清單 (PRD 4 & 7.1)",
    description="透過 UserServiceInterface 回傳 4 大預設測試角色帳號，供評審與使用者免密碼一鍵模擬登入。",
)
async def list_preset_personas(
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> List[UserProfile]:
    """Returns the 4 preset test accounts for quick demo login without passwords."""
    return user_service.list_personas()


@router.post(
    "/mock-login",
    response_model=UserProfile,
    summary="模擬登入 (Demo Login)",
    description="切換為指定的預設 Persona 或自訂訪客探索者帳號。",
)
async def mock_login(
    req: MockLoginRequest,
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> UserProfile:
    """Log in as a preset demo persona or guest without formal authentication (PRD 7.1)."""
    return user_service.mock_login(account_id=req.account_id, custom_name=req.custom_name)


@router.get(
    "/profile",
    response_model=UserProfile,
    summary="取得使用者偏好與收藏狀態",
)
async def get_profile(
    user_id: str = Query(default="demo_weekend_explorer", description="User identifier"),
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> UserProfile:
    """Get profile, interest tags, and bookmarked event IDs."""
    return user_service.get_profile(user_id)


@router.post(
    "/favorites/{event_id}",
    response_model=FavoriteToggleResponse,
    summary="收藏 / 取消收藏活動",
)
async def toggle_favorite(
    event_id: str,
    user_id: str = Query(default="demo_weekend_explorer", description="User identifier"),
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> FavoriteToggleResponse:
    """Add or remove an event from user bookmarks."""
    try:
        return await user_service.toggle_favorite(user_id=user_id, event_id=event_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/favorites",
    response_model=List[Event],
    summary="取得個人收藏活動清單",
)
async def get_favorites(
    user_id: str = Query(default="demo_weekend_explorer", description="User identifier"),
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> List[Event]:
    """Get the full Event objects that the user has favorited."""
    return await user_service.get_favorites(user_id)


@router.put(
    "/preferences",
    response_model=UserProfile,
    summary="更新個人偏好條件",
)
async def update_preferences(
    req: UpdatePreferencesRequest,
    user_id: str = Query(default="demo_weekend_explorer", description="User identifier"),
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> UserProfile:
    """Update user categories, tags, budget, and indoor/crowd preferences."""
    return user_service.update_preferences(user_id=user_id, req=req)
