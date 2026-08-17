from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import get_user_service_dep
from app.models.event import Event
from app.models.user import (
    CalendarConflictCheckRequest,
    CalendarConflictCheckResponse,
    CalendarSyncRequest,
    CalendarSyncResponse,
    FavoriteToggleResponse,
    GoogleAuthConfigResponse,
    GoogleAuthRequest,
    GoogleAuthResponse,
    GoogleCalendarEvent,
    MockLoginRequest,
    UpdatePreferencesRequest,
    UserProfile,
)
from app.services.interfaces import UserServiceInterface

router = APIRouter(prefix="/user", tags=["User & Persona (Mock Login & Google Calendar)"])


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


@router.get(
    "/auth/config",
    response_model=GoogleAuthConfigResponse,
    summary="取得 Google OAuth 2.0 Client 設定",
    description="回傳前端 Google Identity Services (GIS) / OAuth 2.0 Web Client 初始化所需之 Client ID 與設定。",
)
async def get_google_auth_config(
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> GoogleAuthConfigResponse:
    """Get Google OAuth 2.0 Client ID config for frontend Google Sign-In."""
    return user_service.get_google_auth_config()


@router.post(
    "/auth/google",
    response_model=GoogleAuthResponse,
    summary="真實 Google 帳號登入 (Google Sign-In / OAuth 2.0)",
    description="支援透過 Google Identity Services (GIS) JWT Token 或 OAuth 2.0 驗證真實 Google 帳號，並同步使用者真實 Google 個人資料與日曆連動。",
)
async def login_with_google(
    req: GoogleAuthRequest,
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> GoogleAuthResponse:
    """Sign in or register user using real Google account credentials."""
    return user_service.login_google(req)


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
    description="更新使用者感興趣的類別、關鍵字標籤、室內冷氣偏好、避開人潮條件、預算上限與遮蔭導航偏好。",
)
async def update_preferences(
    req: UpdatePreferencesRequest,
    user_id: str = Query(default="demo_weekend_explorer", description="User identifier"),
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> UserProfile:
    """Update user categories, tags, budget, and indoor/crowd preferences."""
    return user_service.update_preferences(user_id=user_id, req=req)


@router.get(
    "/calendar/events",
    response_model=List[GoogleCalendarEvent],
    summary="取得已連動之 Google 日曆行程清單",
    description="取得已連動 Google 帳號中之現有行事曆行程，供活動時間衝突比對與日程預覽。",
)
async def get_calendar_events(
    user_id: str = Query(default="demo_weekend_explorer", description="User identifier"),
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> List[GoogleCalendarEvent]:
    """Retrieve the current Google Calendar event entries for conflict checking."""
    return user_service.get_calendar_events(user_id)


@router.post(
    "/calendar/check-conflict",
    response_model=CalendarConflictCheckResponse,
    summary="比對 Google 日曆時段衝突",
    description="傳入欲排入的 SideQuest 活動時段，自動比對 Google Calendar 現有行程是否存在重疊衝突。",
)
async def check_calendar_conflict(
    req: CalendarConflictCheckRequest,
    user_id: str = Query(default="demo_weekend_explorer", description="User identifier"),
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> CalendarConflictCheckResponse:
    """Check if proposed SideQuest event overlaps with existing calendar commitments."""
    return user_service.check_calendar_conflict(user_id=user_id, req=req)


@router.post(
    "/calendar/sync",
    response_model=CalendarSyncResponse,
    summary="執行 Google 日曆排程同步與衝突調解 (覆蓋 / 並存 / 取消)",
    description="將活動排入 Google 日曆，若有衝突可依使用者決策選擇：覆蓋原有行程 (overwrite)、兩者皆保留 (both)、或取消加入 (cancel)。",
)
async def sync_calendar_event(
    req: CalendarSyncRequest,
    user_id: str = Query(default="demo_weekend_explorer", description="User identifier"),
    user_service: UserServiceInterface = Depends(get_user_service_dep),
) -> CalendarSyncResponse:
    """Sync event to Google Calendar with resolution choice."""
    return user_service.sync_calendar_event(user_id=user_id, req=req)

