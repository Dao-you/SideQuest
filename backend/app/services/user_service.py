"""Mock User and Persona Management Service implementing UserServiceInterface."""

from typing import Dict, List, Optional
from datetime import datetime
from app.config import settings
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
    UpdatePreferencesRequest,
    UserProfile,
)
from app.services.event_service import EventService, get_event_service
from app.services.interfaces import EventServiceInterface, UserServiceInterface


class UserService(UserServiceInterface):
    """Manages user profiles, preset persona accounts, and favorites with interface support."""

    def __init__(self, event_service: Optional[EventServiceInterface] = None) -> None:
        self.event_service = event_service or get_event_service()
        self._users: Dict[str, UserProfile] = {}
        self._init_preset_personas()

    def _init_preset_personas(self) -> None:
        """Seed 4 realistic test persona accounts from PRD Section 4 & 7.1."""
        personas = [
            UserProfile(
                user_id="demo_weekend_explorer",
                name="林小晴 (週末探索者)",
                email="sunny.lin@example.com",
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=60",
                persona_title="週末探索者",
                favorite_categories=["exhibition", "market", "cafe", "craft"],
                favorite_tags=["文創", "市集", "咖啡", "冷氣"],
                favorite_event_ids=["evt_popop_craft_workshop", "evt_clab_future_media"],
                prefer_indoor=True,
                avoid_crowd=True,
                max_budget=500,
                route_preference="shade_first",
                google_account_connected=True,
                google_email="sunny.lin@gmail.com",
                calendar_events=[
                    GoogleCalendarEvent(
                        event_id="gcal_team_sync_01",
                        title="產品設計團隊每週 Sprint 檢討會議",
                        start_time="2026-08-22T14:00:00+08:00",
                        end_time="2026-08-22T16:30:00+08:00",
                        location="信義區松仁路共享會議室",
                        description="Review Q3 User Journey and Hackathon Demo Milestones",
                        category="work",
                        is_sidequest_event=False,
                    ),
                    GoogleCalendarEvent(
                        event_id="gcal_family_dinner_02",
                        title="週日家庭聚餐 · 鼎泰豐",
                        start_time="2026-08-23T18:00:00+08:00",
                        end_time="2026-08-23T20:00:00+08:00",
                        location="信義旗艦店",
                        description="提前訂位保留席",
                        category="personal",
                        is_sidequest_event=False,
                    ),
                ],
            ),
            UserProfile(
                user_id="demo_tech_geek",
                name="陳立威 (技術社群愛好者)",
                email="alex.chen@example.com",
                avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop&q=60",
                persona_title="技術講座與黑客松參與者",
                favorite_categories=["tech", "workshop", "art"],
                favorite_tags=["AI", "技術講座", "Agent", "黑客松", "UX"],
                favorite_event_ids=["evt_tech_devjam_ai_agent", "evt_tech_luma_product_ux"],
                prefer_indoor=True,
                avoid_crowd=False,
                max_budget=800,
                route_preference="fastest",
                google_account_connected=True,
                google_email="alex.chen@gmail.com",
                calendar_events=[
                    GoogleCalendarEvent(
                        event_id="gcal_tech_luma_01",
                        title="AI Agent 架構工作坊 (Online / Hybrid)",
                        start_time="2026-08-22T13:30:00+08:00",
                        end_time="2026-08-22T16:00:00+08:00",
                        location="南港軟體園區育成中心",
                        description="實戰 Vertex AI & Cloud Run 部署",
                        category="meeting",
                        is_sidequest_event=False,
                    ),
                ],
            ),
            UserProfile(
                user_id="demo_crowd_avoider",
                name="張雅筑 (避開人潮者)",
                email="yachu.chang@example.com",
                avatar_url="https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&auto=format&fit=crop&q=60",
                persona_title="不喜歡擁擠者",
                favorite_categories=["art", "cafe", "craft"],
                favorite_tags=["安靜避暑", "免排隊", "地下街直通", "日式建築"],
                favorite_event_ids=["evt_kishuan_literature_tea", "evt_popop_craft_workshop"],
                prefer_indoor=True,
                avoid_crowd=True,
                max_budget=300,
                route_preference="shade_first",
                google_account_connected=True,
                google_email="yachu.chang@gmail.com",
                calendar_events=[
                    GoogleCalendarEvent(
                        event_id="gcal_book_club_01",
                        title="線上讀書會：慢讀台北巷弄",
                        start_time="2026-08-22T15:00:00+08:00",
                        end_time="2026-08-22T17:00:00+08:00",
                        location="Google Meet 線上會議",
                        description="分享紀州庵與台北文學地景",
                        category="personal",
                        is_sidequest_event=False,
                    ),
                ],
            ),
            UserProfile(
                user_id="demo_family_parent",
                name="黃志明 (親子家庭家長)",
                email="jimmy.huang@example.com",
                avatar_url="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&auto=format&fit=crop&q=60",
                persona_title="親子家庭探險家",
                favorite_categories=["family", "tech", "exhibition"],
                favorite_tags=["親子", "教育互動", "室內冷氣", "捷運直達"],
                favorite_event_ids=["evt_ntsec_ai_future_lab", "evt_tmc_pop_music_history"],
                prefer_indoor=True,
                avoid_crowd=True,
                max_budget=1000,
                route_preference="accessible",
                google_account_connected=True,
                google_email="jimmy.huang@gmail.com",
                calendar_events=[
                    GoogleCalendarEvent(
                        event_id="gcal_parent_training_01",
                        title="小學暑期才藝班接送",
                        start_time="2026-08-22T16:00:00+08:00",
                        end_time="2026-08-22T17:30:00+08:00",
                        location="士林國小活動中心",
                        description="準時接駁放學",
                        category="personal",
                        is_sidequest_event=False,
                    ),
                ],
            ),
        ]
        for p in personas:
            self._users[p.user_id] = p

    def list_personas(self) -> List[UserProfile]:
        """Return the 4 preset personas."""
        preset_ids = ["demo_weekend_explorer", "demo_tech_geek", "demo_crowd_avoider", "demo_family_parent"]
        return [self.get_profile(uid) for uid in preset_ids]

    def get_profile(self, user_id: str) -> UserProfile:
        """Fetch user profile or return default guest profile."""
        if user_id in self._users:
            return self._users[user_id]
        return UserProfile(
            user_id=user_id,
            name="訪客探索者",
            email="guest@sidequest.taipei",
            avatar_url="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&auto=format&fit=crop&q=60",
            persona_title="一般市民",
            favorite_categories=["exhibition", "art", "cafe"],
            favorite_tags=["台北", "冷氣", "免費"],
            favorite_event_ids=[],
            prefer_indoor=True,
            avoid_crowd=True,
            max_budget=500,
        )

    def get_user_profile(self, user_id: str) -> UserProfile:
        """Alias for get_profile."""
        return self.get_profile(user_id)

    def mock_login(self, account_id: Optional[str] = None, custom_name: Optional[str] = None) -> UserProfile:
        """Log in as a preset demo account or create a quick guest persona."""
        acc_id = account_id or "demo_weekend_explorer"
        if acc_id in self._users:
            return self._users[acc_id]

        new_user = UserProfile(
            user_id=acc_id,
            name=custom_name or f"探索者 {acc_id[:6]}",
            email=f"{acc_id}@sidequest.taipei",
            avatar_url="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&auto=format&fit=crop&q=60",
            persona_title="自訂探索者",
            favorite_categories=["exhibition", "tech", "cafe"],
            favorite_tags=["台北", "文創", "AI"],
            favorite_event_ids=[],
            prefer_indoor=True,
            avoid_crowd=True,
            max_budget=500,
        )
        self._users[acc_id] = new_user
        return new_user

    async def toggle_favorite(self, user_id: str, event_id: str) -> FavoriteToggleResponse:
        """Add or remove an event ID from user favorites after verifying event existence."""
        event = await self.event_service.get_event_by_id(event_id)
        if not event:
            raise ValueError(f"活動 ID '{event_id}' 不存在")

        user = self.get_profile(user_id)
        if event_id in user.favorite_event_ids:
            user.favorite_event_ids.remove(event_id)
            is_fav = False
            msg = f"已將活動從個人收藏清單中移除"
        else:
            user.favorite_event_ids.append(event_id)
            is_fav = True
            msg = f"已成功將活動加入個人收藏清單！"

        self._users[user.user_id] = user
        return FavoriteToggleResponse(
            event_id=event_id,
            is_favorited=is_fav,
            total_favorites=len(user.favorite_event_ids),
            message=msg,
        )

    async def get_favorites(self, user_id: str) -> List[Event]:
        """Resolve favorited Event objects via event_service."""
        user = self.get_profile(user_id)
        events: List[Event] = []
        for eid in user.favorite_event_ids:
            ev = await self.event_service.get_event_by_id(eid)
            if ev:
                events.append(ev)
        return events

    def update_preferences(self, user_id: str, req: UpdatePreferencesRequest) -> UserProfile:
        """Update user preferences."""
        user = self.get_profile(user_id)
        if req.favorite_categories is not None:
            user.favorite_categories = req.favorite_categories
        if req.favorite_tags is not None:
            user.favorite_tags = req.favorite_tags
        if req.prefer_indoor is not None:
            user.prefer_indoor = req.prefer_indoor
        if req.avoid_crowd is not None:
            user.avoid_crowd = req.avoid_crowd
        if req.max_budget is not None:
            user.max_budget = req.max_budget
        if req.route_preference is not None:
            user.route_preference = req.route_preference
        if req.google_account_connected is not None:
            user.google_account_connected = req.google_account_connected
        if req.google_email is not None:
            user.google_email = req.google_email

        self._users[user.user_id] = user
        return user

    def get_calendar_events(self, user_id: str) -> List[GoogleCalendarEvent]:
        """Fetch active Google Calendar events for the user."""
        user = self.get_profile(user_id)
        return user.calendar_events

    def check_calendar_conflict(self, user_id: str, req: CalendarConflictCheckRequest) -> CalendarConflictCheckResponse:
        """Check if a proposed event overlaps with existing Google Calendar events."""
        user = self.get_profile(user_id)
        conflicts: List[GoogleCalendarEvent] = []

        try:
            req_start = datetime.fromisoformat(req.start_time.replace("Z", "+00:00"))
            req_end = datetime.fromisoformat(req.end_time.replace("Z", "+00:00"))
        except Exception:
            # Fallback if invalid format
            return CalendarConflictCheckResponse(
                has_conflict=False,
                conflicting_events=[],
                message="時間格式無需比對，無衝突",
                suggested_action="proceed",
            )

        for cal_event in user.calendar_events:
            try:
                ev_start = datetime.fromisoformat(cal_event.start_time.replace("Z", "+00:00"))
                ev_end = datetime.fromisoformat(cal_event.end_time.replace("Z", "+00:00"))
                # Overlap check: start1 < end2 and start2 < end1
                if req_start < ev_end and ev_start < req_end:
                    conflicts.append(cal_event)
            except Exception:
                continue

        if conflicts:
            conf_titles = "、".join([f"【{c.title}】" for c in conflicts])
            return CalendarConflictCheckResponse(
                has_conflict=True,
                conflicting_events=conflicts,
                message=f"偵測到 Google 日曆時間衝突！同時段已排定 {conf_titles}",
                suggested_action="choose_resolution",
            )
        else:
            return CalendarConflictCheckResponse(
                has_conflict=False,
                conflicting_events=[],
                message="Google 日曆同時段為空檔，可直接排入！",
                suggested_action="proceed",
            )

    def sync_calendar_event(self, user_id: str, req: CalendarSyncRequest) -> CalendarSyncResponse:
        """Add, replace or dual-schedule an event in Google Calendar based on user decision."""
        user = self.get_profile(user_id)

        new_cal_event = GoogleCalendarEvent(
            event_id=f"gcal_sq_{req.event_id}_{int(datetime.now().timestamp())}",
            title=req.event_title,
            start_time=req.start_time,
            end_time=req.end_time,
            location=req.location or "台北市",
            description=req.description or "SideQuest 智慧城市探險行程",
            category="sidequest",
            is_sidequest_event=True,
        )

        if req.resolution_choice == "overwrite":
            # Remove any overlapping events
            try:
                req_start = datetime.fromisoformat(req.start_time.replace("Z", "+00:00"))
                req_end = datetime.fromisoformat(req.end_time.replace("Z", "+00:00"))
                remaining = []
                for ev in user.calendar_events:
                    ev_start = datetime.fromisoformat(ev.start_time.replace("Z", "+00:00"))
                    ev_end = datetime.fromisoformat(ev.end_time.replace("Z", "+00:00"))
                    if not (req_start < ev_end and ev_start < req_end):
                        remaining.append(ev)
                remaining.append(new_cal_event)
                user.calendar_events = remaining
                msg = f"已成功覆蓋原有行程，並將【{req.event_title}】排入 Google 日曆！"
                action_taken = "overwritten"
            except Exception:
                user.calendar_events.append(new_cal_event)
                msg = f"已將【{req.event_title}】加入 Google 日曆！"
                action_taken = "added"
        elif req.resolution_choice == "both":
            new_cal_event.description = f"⚠️ 提醒：與原行程同時段並存。\n{new_cal_event.description}"
            user.calendar_events.append(new_cal_event)
            msg = f"已保留原行程，並將新活動【{req.event_title}】同時排入 Google 日曆！"
            action_taken = "both_kept"
        else: # cancel / keep_existing
            msg = f"已取消加入，保留原 Google 日曆行程。"
            action_taken = "cancelled"
            return CalendarSyncResponse(
                success=True,
                synced_event=None,
                action_taken=action_taken,
                message=msg,
                all_calendar_events=user.calendar_events,
            )

        self._users[user.user_id] = user
        return CalendarSyncResponse(
            success=True,
            synced_event=new_cal_event,
            action_taken=action_taken,
            message=msg,
            all_calendar_events=user.calendar_events,
        )

    def get_google_auth_config(self) -> GoogleAuthConfigResponse:
        """Fetch Google OAuth 2.0 Web Client configuration."""
        client_id = settings.GOOGLE_CLIENT_ID or "917216410511-1tupuplbm4bnr76j7g9r4uii8i84olru.apps.googleusercontent.com"
        return GoogleAuthConfigResponse(
            client_id=client_id,
            enabled=True,
        )

    def login_google(self, req: GoogleAuthRequest) -> GoogleAuthResponse:
        """Authenticate user with real Google Account identity or token."""
        google_email = (req.email or "").strip()
        google_name = (req.name or "").strip()
        google_picture = (req.picture or "").strip()
        google_sub = (req.sub or "").strip()

        # 1. If Google ID Token is provided, decode or verify it
        if req.id_token:
            try:
                from google.oauth2 import id_token
                from google.auth.transport import requests as google_requests
                client_id = settings.GOOGLE_CLIENT_ID or None
                id_info = id_token.verify_oauth2_token(
                    req.id_token,
                    google_requests.Request(),
                    audience=client_id,
                )
                google_email = id_info.get("email", google_email)
                google_name = id_info.get("name", google_name)
                google_picture = id_info.get("picture", google_picture)
                google_sub = id_info.get("sub", google_sub)
            except Exception:
                # If strict verification failed, decode unverified JWT payload
                import base64
                import json
                try:
                    parts = req.id_token.split(".")
                    if len(parts) >= 2:
                        padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                        payload_bytes = base64.urlsafe_b64decode(padded)
                        payload = json.loads(payload_bytes.decode("utf-8"))
                        google_email = payload.get("email", google_email)
                        google_name = payload.get("name", google_name)
                        google_picture = payload.get("picture", google_picture)
                        google_sub = payload.get("sub", google_sub)
                except Exception:
                    pass

        if not google_email:
            google_email = "google.user@gmail.com"
        if not google_name:
            google_name = google_email.split("@")[0].capitalize()
        if not google_sub:
            google_sub = str(abs(hash(google_email)))

        # Unique user ID for Google account
        user_id = f"google_{google_sub[:16]}"

        if user_id in self._users:
            user = self._users[user_id]
            user.name = google_name or user.name
            user.email = google_email
            user.google_email = google_email
            if google_picture:
                user.avatar_url = google_picture
            user.google_account_connected = True
            user.is_mock_account = False
            user.auth_provider = "google"
            user.google_sub = google_sub
        else:
            user = UserProfile(
                user_id=user_id,
                name=google_name,
                email=google_email,
                avatar_url=google_picture or f"https://api.dicebear.com/7.x/bottts/svg?seed={google_email}",
                persona_title="Google 認證使用者",
                favorite_categories=["exhibition", "tech", "cafe", "music"],
                favorite_tags=["AI", "科技", "文創", "市集", "咖啡"],
                favorite_event_ids=["evt_devjam_taipei_2026", "evt_popop_craft_workshop"],
                prefer_indoor=True,
                avoid_crowd=True,
                max_budget=800,
                route_preference="shade_first",
                google_account_connected=True,
                google_email=google_email,
                calendar_events=[
                    GoogleCalendarEvent(
                        event_id=f"gcal_sync_team_{user_id}",
                        title="產品設計團隊每週 Sprint 檢討會議",
                        start_time="2026-08-22T14:00:00+08:00",
                        end_time="2026-08-22T16:30:00+08:00",
                        location="信義區松仁路共享會議室",
                        description="Google Calendar 雙向同步行事曆事件",
                        category="work",
                        is_sidequest_event=False,
                    )
                ],
                is_mock_account=False,
                auth_provider="google",
                google_sub=google_sub,
            )
            self._users[user_id] = user

        return GoogleAuthResponse(
            success=True,
            user=user,
            message=f"已成功以 Google 帳號 ({google_email}) 登入 SideQuest！",
            auth_method="google_oauth2",
        )



_user_service_instance: Optional[UserService] = None


def get_user_service() -> UserService:
    """Singleton getter for UserService."""
    global _user_service_instance
    if _user_service_instance is None:
        _user_service_instance = UserService()
    return _user_service_instance
