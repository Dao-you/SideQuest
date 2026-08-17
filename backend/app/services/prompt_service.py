"""Prompt Metadata and Homepage Example Prompts Service with Interface."""

from typing import List, Optional
from app.models.agent import QuickPromptItem, QuickPromptsResponse, QuickTagItem
from app.services.interfaces import PromptMetadataServiceInterface


class PromptMetadataService(PromptMetadataServiceInterface):
    """Provides homepage example prompts and quick filter tags without hardcoding in API endpoints."""

    def __init__(self) -> None:
        self._cached_prompts: Optional[QuickPromptsResponse] = None

    def get_quick_prompts(self) -> QuickPromptsResponse:
        """Fetch curated example prompts and filter chips (dynamically configurable)."""
        if self._cached_prompts is not None:
            return self._cached_prompts

        example_prompts = [
            QuickPromptItem(
                title="免費文藝探索",
                prompt="這週六下午，台北有什麼免費展覽或市集？",
                category="exhibition",
                icon="🎨",
            ),
            QuickPromptItem(
                title="AI 與技術小聚",
                prompt="最近台北有沒有 AI、產品或創業社群小聚？",
                category="tech",
                icon="🤖",
            ),
            QuickPromptItem(
                title="臨時放鬆避開人潮",
                prompt="我在中山區，有兩個小時空檔，想找有冷氣又不想去太擠的地方。",
                category="crowd_avoid",
                icon="☕",
            ),
            QuickPromptItem(
                title="捷運遮蔭散策",
                prompt="找捷運直達、300 元以內的室內展覽，避開烈日曝曬。",
                category="transit_shade",
                icon="🚇",
            ),
        ]

        quick_tags = [
            QuickTagItem(id="tag_weekend", label="本週末", icon="📅", filter_key="time", filter_value="weekend"),
            QuickTagItem(id="tag_free", label="免費活動", icon="🎟️", filter_key="price_type", filter_value="free"),
            QuickTagItem(id="tag_indoor", label="室內冷氣", icon="❄️", filter_key="is_indoor", filter_value=True),
            QuickTagItem(id="tag_avoid_crowd", label="避開人潮", icon="✨", filter_key="avoid_crowd", filter_value=True),
            QuickTagItem(id="tag_tech", label="技術與小聚", icon="💻", filter_key="category", filter_value="tech"),
            QuickTagItem(id="tag_family", label="親子體驗", icon="👨‍👩‍👧", filter_key="category", filter_value="family"),
            QuickTagItem(id="tag_nearby", label="捷運附近", icon="📍", filter_key="nearby", filter_value=True),
        ]

        self._cached_prompts = QuickPromptsResponse(
            example_prompts=example_prompts,
            quick_tags=quick_tags,
        )
        return self._cached_prompts


_prompt_service_instance: Optional[PromptMetadataService] = None


def get_prompt_metadata_service() -> PromptMetadataService:
    """Singleton getter for PromptMetadataService."""
    global _prompt_service_instance
    if _prompt_service_instance is None:
        _prompt_service_instance = PromptMetadataService()
    return _prompt_service_instance
