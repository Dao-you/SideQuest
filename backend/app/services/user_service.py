"""Mock User and Persona Management Service for PRD MVP."""

from typing import Dict, List, Optional
from app.models.user import UserProfile, FavoriteToggleResponse


class UserService:
    """Manages mock user profiles, preset persona accounts, and favorites."""

    def __init__(self) -> None:
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
            ),
        ]
        for p in personas:
            self._users[p.user_id] = p

    def get_user_profile(self, user_id: str) -> UserProfile:
        """Fetch user profile or return default guest profile."""
        if user_id in self._users:
            return self._users[user_id]
        # Return fallback guest user
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

    def mock_login(self, account_id: Optional[str] = None, custom_name: Optional[str] = None) -> UserProfile:
        """Log in as a preset demo account or create a quick guest persona."""
        acc_id = account_id or "demo_weekend_explorer"
        if acc_id in self._users:
            return self._users[acc_id]
        
        # Create new custom mock account
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

    def toggle_favorite(self, user_id: str, event_id: str) -> FavoriteToggleResponse:
        """Add or remove an event ID from user favorites."""
        user = self.get_user_profile(user_id)
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

    def update_preferences(
        self,
        user_id: str,
        favorite_categories: Optional[List[str]] = None,
        favorite_tags: Optional[List[str]] = None,
        prefer_indoor: Optional[bool] = None,
        avoid_crowd: Optional[bool] = None,
        max_budget: Optional[int] = None,
    ) -> UserProfile:
        """Update user preferences."""
        user = self.get_user_profile(user_id)
        if favorite_categories is not None:
            user.favorite_categories = favorite_categories
        if favorite_tags is not None:
            user.favorite_tags = favorite_tags
        if prefer_indoor is not None:
            user.prefer_indoor = prefer_indoor
        if avoid_crowd is not None:
            user.avoid_crowd = avoid_crowd
        if max_budget is not None:
            user.max_budget = max_budget

        self._users[user.user_id] = user
        return user


_user_service_instance: Optional[UserService] = None


def get_user_service() -> UserService:
    """Singleton getter for UserService."""
    global _user_service_instance
    if _user_service_instance is None:
        _user_service_instance = UserService()
    return _user_service_instance
