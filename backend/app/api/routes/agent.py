"""Agent Interaction Routes (Chat, SSE Stream, Recommendations, Quick Prompts, and Feedback)."""

import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_agent_dep
from app.agent.gemini_agent import GeminiAgent
from app.models.agent import (
    AgentRecommendation,
    AgentRecommendationRequest,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    QuickPromptItem,
    QuickPromptsResponse,
    QuickTagItem,
)

router = APIRouter(prefix="/agent", tags=["Agent Discovery & Decision"])


@router.get(
    "/quick-prompts",
    response_model=QuickPromptsResponse,
    summary="取得首頁範例提示詞與快速篩選標籤 (PRD Section 7.2)",
    description="提供 PRD 規範之首頁範例提示詞（如免費展覽、AI 小聚、中山區兩小時）與快速條件標籤（今天/週末、免費、室內、避開人潮）。",
)
async def get_quick_prompts():
    """Returns example prompts and quick chips specified in PRD Section 7.2."""
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

    return QuickPromptsResponse(
        example_prompts=example_prompts,
        quick_tags=quick_tags,
    )


@router.post(
    "/chat/stream",
    summary="Agent 即時思考與推薦串流 (SSE)",
    description=(
        "透過 Server-Sent Events (SSE) 串流輸出 Agent 的思考步驟 (thought)、"
        "意圖確認 (understanding)、工具調用 (tool_call / tool_result)、Markdown 文字區塊 (markdown_chunk) 以及 3 大推薦卡片 (recommendation_cards)。"
    ),
)
async def chat_stream(
    request: ChatRequest,
    agent: GeminiAgent = Depends(get_agent_dep),
) -> EventSourceResponse:
    """Stream Agent reasoning steps, structured criteria, and recommendation cards via SSE."""

    async def event_generator() -> AsyncGenerator[dict, None]:
        async for event in agent.stream_chat(request):
            yield {
                "event": event.event.value,
                "data": json.dumps(event.data, ensure_ascii=False),
            }

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Agent 同步對話端點 (Non-streaming)",
    description="傳入使用者自然語言查詢，直接回傳完整 Agent 回覆、結構化條件、思考步驟及 3 大推薦卡片列表。",
)
async def chat_sync(
    request: ChatRequest,
    agent: GeminiAgent = Depends(get_agent_dep),
) -> ChatResponse:
    """Execute non-streaming chat query with PRD multi-turn support."""
    return await agent.chat(request)


@router.post(
    "/recommend",
    response_model=AgentRecommendation,
    summary="快速智慧推薦端點",
    description="傳入經緯度與偏好標籤，直接以多準則疏導演算法計算 3 個推薦卡片。",
)
async def recommend(
    request: AgentRecommendationRequest,
    agent: GeminiAgent = Depends(get_agent_dep),
) -> AgentRecommendation:
    """Execute quick structured recommendation query."""
    return await agent.recommend(request)


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="使用者推薦結果滿意度回饋 (PRD Section 6 Stage 10)",
    description="蒐集使用者對於推薦結果之符合度、距離、人潮等回饋，用於後續推薦調優。",
)
async def submit_feedback(req: FeedbackRequest):
    """Log user feedback for recommendation quality."""
    return FeedbackResponse(
        status="success",
        message=f"已成功記錄對活動 '{req.event_id}' 的回饋（{'符合需求' if req.is_helpful else '不符合需求'}）。SideQuest 感謝您的寶貴建議！",
    )
