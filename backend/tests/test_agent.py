"""Tests for Agent Chat, SSE Streaming, and Recommendation Engine."""

import pytest
from app.agent.gemini_agent import get_gemini_agent
from app.models.agent import AgentRecommendationRequest, ChatRequest, SSEEventType


@pytest.mark.asyncio
async def test_agent_stream_chat():
    """Verify SSE stream emits thought steps, tool traces, text chunks, and recommendation cards."""
    agent = get_gemini_agent()
    request = ChatRequest(
        message="今天下午信義區好熱，想找個捷運方便、有冷氣的展覽或手作，不要人擠人",
        user_latitude=25.0330,
        user_longitude=121.5654,
        avoid_crowd_strict=True,
    )

    received_events = []
    async for event in agent.stream_chat(request):
        received_events.append(event)

    event_types = {e.event for e in received_events}
    assert SSEEventType.THOUGHT in event_types
    assert SSEEventType.TOOL_CALL in event_types
    assert SSEEventType.TOOL_RESULT in event_types
    assert SSEEventType.MARKDOWN_CHUNK in event_types
    assert SSEEventType.RECOMMENDATION_CARDS in event_types
    assert SSEEventType.DONE in event_types

    # Verify cards payload
    card_events = [e for e in received_events if e.event == SSEEventType.RECOMMENDATION_CARDS]
    assert len(card_events) == 1
    cards_data = card_events[0].data["cards"]
    assert len(cards_data) > 0
    assert "total_score" in cards_data[0]
    assert "badges" in cards_data[0]


@pytest.mark.asyncio
async def test_agent_sync_chat():
    """Test non-streaming chat execution."""
    agent = get_gemini_agent()
    request = ChatRequest(
        message="推薦松山或南港附近安靜看展喝咖啡的地方",
        user_latitude=25.0438,
        user_longitude=121.5607,
    )

    res = await agent.chat(request)
    assert res.session_id is not None
    assert len(res.reply) > 50
    assert len(res.thought_steps) >= 3
    assert len(res.recommendations) > 0


@pytest.mark.asyncio
async def test_agent_quick_recommend():
    """Test fast structured recommendation endpoint."""
    agent = get_gemini_agent()
    request = AgentRecommendationRequest(
        user_latitude=25.0330,
        user_longitude=121.5654,
        interests=["art", "cafe"],
        avoid_crowd=True,
        limit=3,
    )

    res = await agent.recommend(request)
    assert len(res.recommendations) == 3
    assert res.total_evaluated > 0
    assert len(res.dispersal_insights) > 0
