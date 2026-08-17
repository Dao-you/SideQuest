"""Tests for PRD Compliance: Mock User Personas, Favorites, Quick Prompts, 3-Card Roles, and Multi-turn Refinement."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.agent.gemini_agent import get_gemini_agent
from app.models.agent import ChatRequest
from app.models.event import CardRole


@pytest.mark.asyncio
async def test_user_personas_and_mock_login():
    """Verify PRD 7.1 Mock Personas and Login without authentication."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. List 4 preset personas
        res = await client.get("/api/v1/user/personas")
        assert res.status_code == 200
        personas = res.json()
        assert len(personas) == 4
        assert any(p["user_id"] == "demo_weekend_explorer" for p in personas)
        assert any(p["user_id"] == "demo_tech_geek" for p in personas)

        # 2. Mock login as tech geek
        login_res = await client.post(
            "/api/v1/user/mock-login",
            json={"account_id": "demo_tech_geek"},
        )
        assert login_res.status_code == 200
        user = login_res.json()
        assert user["user_id"] == "demo_tech_geek"
        assert "tech" in user["favorite_categories"]

        # 3. Toggle favorite event
        fav_res = await client.post(
            "/api/v1/user/favorites/evt_tech_devjam_ai_agent?user_id=demo_weekend_explorer",
        )
        assert fav_res.status_code == 200
        fav_data = fav_res.json()
        assert fav_data["is_favorited"] is True

        # 4. Get favorite events
        list_fav = await client.get("/api/v1/user/favorites?user_id=demo_weekend_explorer")
        assert list_fav.status_code == 200
        fav_events = list_fav.json()
        assert any(e["id"] == "evt_tech_devjam_ai_agent" for e in fav_events)


@pytest.mark.asyncio
async def test_quick_prompts_and_feedback():
    """Verify PRD 7.2 Quick Prompts and Stage 10 Feedback."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Quick Prompts & Tags
        res = await client.get("/api/v1/agent/quick-prompts")
        assert res.status_code == 200
        data = res.json()
        assert len(data["example_prompts"]) >= 3
        assert len(data["quick_tags"]) >= 5

        # 2. Feedback submission
        fb_res = await client.post(
            "/api/v1/agent/feedback",
            json={
                "session_id": "sess_test_123",
                "event_id": "evt_popop_craft_workshop",
                "is_helpful": True,
                "feedback_tag": "accurate",
                "comment": "推薦非常舒適，冷氣充足而且人少！",
            },
        )
        assert fb_res.status_code == 200
        assert fb_res.json()["status"] == "success"


@pytest.mark.asyncio
async def test_3_card_roles_and_parsed_criteria():
    """Verify PRD 7.3 Structured Criteria and PRD 7.4 3 Distinct Card Roles."""
    agent = get_gemini_agent()

    # Query asking for Tech & AI meetups
    req = ChatRequest(
        message="這週六下午台北有什麼免費的 AI 或技術小聚？不想去太擠的地方",
        avoid_crowd_strict=True,
    )
    res = await agent.chat(req)

    # 1. Verify structured criteria extracted (PRD 7.3)
    assert res.parsed_criteria is not None
    assert res.parsed_criteria.is_free_only is True or res.parsed_criteria.avoid_crowd is True
    assert any("AI" in i or "技術" in i for i in res.parsed_criteria.interests)

    # 2. Verify 3 recommendation cards (PRD 7.4)
    assert len(res.recommendations) == 3
    card_roles = [c.card_role for c in res.recommendations]
    assert CardRole.TOP_MATCH in card_roles
    assert CardRole.DISPERSAL_ALTERNATIVE in card_roles
