"""Tests for Crowd Dispersal Ranking Algorithm and Scoring Engine."""

import pytest
from app.agent.ranking_engine import ranking_engine
from app.models.event import CardRole, DispersalBadgeType
from app.services.firestore_service import get_firestore_service
from app.services.maps_service import get_maps_service


@pytest.mark.asyncio
async def test_ranking_engine_crowd_dispersal():
    """Verify that crowd dispersal algorithm penalizes overcrowded venues and promotes hidden gems."""
    firestore = get_firestore_service()
    maps = get_maps_service()

    events = await firestore.get_events()
    venues = await firestore.get_all_venues()
    venues_map = {v.venue_id: v for v in venues}
    weather = await maps.get_microclimate(25.0330, 121.5654)

    # User looking for craft/workshop: Huashan/Songshan (crowded 85-92) vs Bottle Cap Factory (low 28)
    query = "想找手作市集或木工體驗，有冷氣不要人擠人"

    routes_map = {}
    for ev in events:
        route = await maps.compute_route(
            origin_lat=25.0330,
            origin_lng=121.5654,
            dest_lat=ev.location.latitude,
            dest_lng=ev.location.longitude,
            dest_name=ev.venue_name,
        )
        routes_map[ev.id] = route

    cards = ranking_engine.rank_and_build_cards(
        events=events,
        venues_map=venues_map,
        weather=weather,
        routes_map=routes_map,
        query_text=query,
        avoid_crowd_strict=True,
    )

    assert len(cards) == 3

    # Top recommendation should be a high quality, low crowd event (e.g., Popop Bottle Cap Factory or C-LAB)
    top_card = cards[0]
    assert top_card.crowd_score <= 50
    assert any(b.type == DispersalBadgeType.HIDDEN_GEM for b in top_card.badges) or any(b.type == DispersalBadgeType.COOL_HAVEN for b in top_card.badges)

    # Verify 3 distinct PRD card roles
    assert cards[0].card_role == CardRole.TOP_MATCH
    assert cards[1].card_role == CardRole.DISPERSAL_ALTERNATIVE

    # When query specifically searches for crowded event (文博會 / 松山市集), check crowd warning badge
    crowded_query_cards = ranking_engine.rank_and_build_cards(
        events=events,
        venues_map=venues_map,
        weather=weather,
        routes_map=routes_map,
        query_text="2026 臺灣文博會",
        avoid_crowd_strict=False,
    )
    assert len(crowded_query_cards) > 0
    wenbo_card = crowded_query_cards[0]
    if wenbo_card.crowd_score >= 80:
        assert any(b.type == DispersalBadgeType.CROWD_WARNING for b in wenbo_card.badges)
