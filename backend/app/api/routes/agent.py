"""Agent Interaction Routes using Service Interfaces (Chat, SSE Stream, Recommendations, Quick Prompts, and Feedback)."""

import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.agent.gemini_agent import GeminiAgent
from app.api.deps import (
    get_agent_dep,
    get_feedback_service_dep,
    get_prompt_metadata_dep,
)
from app.models.agent import (
    AgentRecommendation,
    AgentRecommendationRequest,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    QuickPromptsResponse,
)
from app.services.interfaces import (
    FeedbackServiceInterface,
    PromptMetadataServiceInterface,
)

router = APIRouter(prefix="/agent", tags=["Agent Discovery & Decision"])


@router.get(
    "/quick-prompts",
    response_model=QuickPromptsResponse,
    summary="取得首頁範例提示詞與快速篩選標籤 (PRD Section 7.2)",
    description="透過 PromptMetadataServiceInterface 提供首頁範例提示詞與快速條件標籤，支援動態擴充與測試。",
)
async def get_quick_prompts(
    prompt_service: PromptMetadataServiceInterface = Depends(get_prompt_metadata_dep),
) -> QuickPromptsResponse:
    """Retrieve example prompts and quick filter tags from service."""
    return prompt_service.get_quick_prompts()


@router.post(
    "/chat/stream",
    summary="Agent 即時思考與推薦串流 (SSE)",
    description=(
        "透過 Server-Sent Events (SSE) 串流輸出 Agent 的思考步驟 (thought)、"
        "意圖確認 (understanding，包含 normalized requested_date)、工具調用 (tool_call / tool_result)、"
        "Markdown 文字區塊 (markdown_chunk) 以及 3 大推薦卡片 (recommendation_cards)。"
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
    description="傳入包含日期、時間、約會情境與活動偏好的自然語言查詢，直接回傳完整 Agent 回覆、"
    "結構化日期條件、思考步驟及 3 大推薦卡片列表；指定日期會篩選活動日期／時段交集。",
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
    description="透過 FeedbackServiceInterface 記錄使用者對於推薦結果之符合度、距離、人潮等回饋，自動持久化至 Firestore 或記憶體中。",
)
async def submit_feedback(
    req: FeedbackRequest,
    feedback_service: FeedbackServiceInterface = Depends(get_feedback_service_dep),
) -> FeedbackResponse:
    """Log user feedback for recommendation quality."""
    return await feedback_service.submit_feedback(req)
