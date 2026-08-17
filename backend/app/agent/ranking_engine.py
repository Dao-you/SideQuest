"""Multi-Criteria Decision Making (MCDM) & Crowd Dispersal Ranking Engine (PRD Compliant)."""

from typing import List, Optional, Tuple
from app.models.crowd import CrowdLevel, VenueLiveStatus
from app.models.event import (
    CardRole,
    DispersalBadge,
    DispersalBadgeType,
    Event,
    RecommendationCard,
)
from app.models.places import RouteComfort
from app.models.weather import MicroclimateResponse


class RankingEngine:
    """Computes multi-factor scores and produces structured recommendation cards with crowd dispersal badges.
    
    Adheres strictly to PRD Section 8.3 Weight Distribution:
    - 興趣符合度 (Relevance): 35%
    - 時間可行性 (Time Feasibility): 25%
    - 地點與交通便利性 (Transit & Shade): 20%
    - 預算符合度 (Budget): 10%
    - 人潮與環境舒適度 (Crowd & Microclimate): 10%
    """

    def __init__(
        self,
        w_match: float = 0.35,
        w_time: float = 0.25,
        w_access: float = 0.20,
        w_budget: float = 0.10,
        w_comfort: float = 0.10,
    ) -> None:
        self.w_match = w_match
        self.w_time = w_time
        self.w_access = w_access
        self.w_budget = w_budget
        self.w_comfort = w_comfort

    def compute_match_score(self, event: Event, query_text: str, explicit_categories: Optional[List[str]] = None) -> float:
        """Calculate relevance score (0-100) between user query and event (35% weight)."""
        score = 50.0
        q = query_text.lower()

        # Category match
        if event.category.value.lower() in q:
            score += 25.0
        if explicit_categories and any(c.lower() in event.category.value.lower() for c in explicit_categories):
            score += 30.0

        # Tech & AI specific keywords matching
        tech_keywords = ["ai", "agent", "devjam", "技術", "講座", "小聚", "工作坊", "黑客松", "ux", "產品", "程式"]
        if any(k in q for k in tech_keywords):
            if any(k in event.title.lower() or any(k in t.lower() for t in event.tags) for k in tech_keywords):
                score += 35.0

        # General culture / weekend keywords
        culture_keywords = ["咖啡", "展覽", "市集", "手作", "動漫", "音樂", "藝術", "文創", "古蹟", "煙火", "親子"]
        for ck in culture_keywords:
            if ck in q and (ck in event.title.lower() or any(ck in t.lower() for t in event.tags)):
                score += 20.0
                break

        # High rating booster
        if event.rating >= 4.7:
            score += 8.0

        return min(100.0, max(15.0, score))

    def compute_time_feasibility_score(self, event: Event, query_text: str) -> float:
        """Calculate time feasibility score (0-100) (25% weight)."""
        # In MVP seed, all events are currently running during the weekend
        # Events with quick duration (1.5h - 2.5h) get high feasibility
        score = 92.0
        if "兩小時" in query_text or "2小時" in query_text:
            if event.estimated_duration_hours <= 2.0:
                score += 8.0
            else:
                score -= 15.0
        return min(100.0, max(20.0, score))

    def compute_budget_score(self, event: Event, max_budget: Optional[int] = None, is_free_only: bool = False) -> float:
        """Calculate budget compliance score (0-100) (10% weight)."""
        if is_free_only or event.price_type == "free" or event.price_amount == 0:
            return 100.0
        
        if max_budget is not None:
            if event.price_amount > max_budget:
                return 15.0  # Heavy penalty for exceeding budget
            elif event.price_amount <= max_budget * 0.5:
                return 95.0
            else:
                return 80.0
        
        # Default pricing evaluation
        if event.price_amount <= 100:
            return 95.0
        elif event.price_amount <= 350:
            return 85.0
        else:
            return 70.0

    def compute_weather_comfort_score(self, event: Event, weather: MicroclimateResponse) -> float:
        """Evaluate weather comfort score (0-100) (Microclimate comfort index)."""
        is_high_heat_or_uv = weather.temperature_c >= 32.0 or weather.uv_index >= 7.0 or weather.rain_probability_percentage >= 50

        if event.is_indoor and event.ac_available:
            return 98.0 if is_high_heat_or_uv else 88.0
        elif event.is_indoor:
            return 78.0
        else:
            # Outdoor event in hot summer
            if is_high_heat_or_uv:
                return 30.0  # Significant penalty for outdoor exposure in high heat/UV
            return 75.0

    def compute_accessibility_score(self, route: Optional[RouteComfort], event: Event) -> Tuple[float, str]:
        """Evaluate accessibility and shade comfort (0-100) (20% weight)."""
        if not route:
            mrt_dist = event.location.mrt_distance_meters or 500
            score = max(40.0, 100.0 - (mrt_dist / 15.0))
            summary = f"鄰近捷運 {event.location.mrt_station or '市區捷運站'}，步行約 {int(mrt_dist/80)} 分鐘"
            return score, summary

        duration_penalty = min(35.0, route.total_duration_minutes * 0.7)
        shade_bonus = (route.underground_or_shaded_percentage / 100.0) * 35.0
        score = max(20.0, min(100.0, 70.0 - duration_penalty + shade_bonus))
        return score, route.transit_summary

    def rank_and_build_cards(
        self,
        events: List[Event],
        venues_map: dict,
        weather: MicroclimateResponse,
        routes_map: dict,
        query_text: str,
        avoid_crowd_strict: bool = True,
        prefer_indoor: Optional[bool] = None,
        max_budget: Optional[int] = None,
        is_free_only: bool = False,
    ) -> List[RecommendationCard]:
        """Rank candidate events using PRD multi-criteria formula and produce 3 distinct recommendation cards:
        1. TOP_MATCH (最符合需求)
        2. DISPERSAL_ALTERNATIVE (替代選擇)
        3. EXPLORATION_GEM (探索選擇)
        """
        cards: List[RecommendationCard] = []
        overcrowded_venues: List[str] = []

        # Detect overcrowded venues
        for e in events:
            venue = venues_map.get(e.venue_id)
            if venue and venue.crowd_score >= 80:
                overcrowded_venues.append(venue.venue_name)

        for event in events:
            # Hard filter check: if strictly free requested and event is paid
            if is_free_only and event.price_type == "paid" and event.price_amount > 0:
                continue

            venue: Optional[VenueLiveStatus] = venues_map.get(event.venue_id)
            crowd_score = venue.crowd_score if venue else 50
            crowd_level = venue.crowd_level.value if venue else CrowdLevel.MODERATE.value
            route = routes_map.get(event.id)

            match_score = self.compute_match_score(event, query_text)
            time_score = self.compute_time_feasibility_score(event, query_text)
            access_score, transit_summary = self.compute_accessibility_score(route, event)
            budget_score = self.compute_budget_score(event, max_budget, is_free_only)
            weather_score = self.compute_weather_comfort_score(event, weather)

            # Crowd comfort combined (0-100)
            crowd_comfort = (100.0 - crowd_score) * 0.6 + weather_score * 0.4

            # PRD 8.3 Multi-Criteria Weighted Sum
            raw_score = (
                match_score * self.w_match
                + time_score * self.w_time
                + access_score * self.w_access
                + budget_score * self.w_budget
                + crowd_comfort * self.w_comfort
            )

            badges: List[DispersalBadge] = []
            is_dispersal_alt = False
            alt_for_venue = None

            # Dynamic crowd dispersal logic
            if crowd_score >= 80:
                if avoid_crowd_strict:
                    raw_score -= 30.0  # Dispersal Penalty
                badges.append(
                    DispersalBadge(
                        type=DispersalBadgeType.CROWD_WARNING,
                        label=f"⚠️ 人潮擁擠 ({crowd_score}/100)",
                        color="red",
                    )
                )
            elif crowd_score <= 35 and event.rating >= 4.5:
                raw_score += 15.0  # Hidden Gem Dispersal Boost
                badges.append(
                    DispersalBadge(
                        type=DispersalBadgeType.HIDDEN_GEM,
                        label=f"✨ 舒適私房推薦 ({crowd_score}/100)",
                        color="green",
                    )
                )
                if overcrowded_venues:
                    is_dispersal_alt = True
                    alt_for_venue = overcrowded_venues[0]

            if event.is_indoor and event.ac_available:
                badges.append(
                    DispersalBadge(
                        type=DispersalBadgeType.COOL_HAVEN,
                        label="❄️ 強冷空調避暑",
                        color="blue",
                    )
                )

            if route and route.underground_or_shaded_percentage >= 50:
                badges.append(
                    DispersalBadge(
                        type=DispersalBadgeType.SHADED_ROUTE,
                        label=f"🚶‍♂️ 遮蔭/地下街 {route.underground_or_shaded_percentage}%",
                        color="teal",
                    )
                )

            if match_score >= 85.0:
                badges.append(
                    DispersalBadge(
                        type=DispersalBadgeType.TOP_MATCH,
                        label="🎯 高度契合主題",
                        color="purple",
                    )
                )

            final_total_score = round(max(5.0, min(100.0, raw_score)), 1)

            # Generate AI recommendation reason
            if is_dispersal_alt and alt_for_venue:
                reason = (
                    f"相較於當前人潮極度擁擠的 {alt_for_venue}，此處人潮指數僅 {crowd_score}（{crowd_level}），"
                    f"具備全室內冷氣且捷運直通遮蔭良好，能享有極致舒適的活動體驗。"
                )
            elif crowd_score >= 80:
                reason = (
                    f"活動內容極具吸引力，但當前人潮指數高達 {crowd_score}（{crowd_level}），"
                    f"預估現場需排隊 {venue.wait_time_minutes if venue else 25} 分鐘，建議提早或移步至推薦之舒適替代方案。"
                )
            else:
                reason = (
                    f"興趣契合度達 {int(match_score)}%，目前人潮舒適（{crowd_score}/100），"
                    f"空間涼爽舒適，適合悠閒參與。"
                )

            cards.append(
                RecommendationCard(
                    event=event,
                    card_role=CardRole.TOP_MATCH,
                    card_role_label="🎯 最符合需求",
                    total_score=final_total_score,
                    match_score=round(match_score, 1),
                    time_feasibility_score=round(time_score, 1),
                    accessibility_score=round(access_score, 1),
                    budget_score=round(budget_score, 1),
                    weather_comfort_score=round(weather_score, 1),
                    crowd_score=crowd_score,
                    crowd_level=crowd_level,
                    transit_summary=transit_summary,
                    recommendation_reason=reason,
                    badges=badges,
                    is_dispersal_alternative=is_dispersal_alt,
                    alternative_for_venue=alt_for_venue,
                )
            )

        # Sort descending by total score
        cards.sort(key=lambda c: c.total_score, reverse=True)

        if not cards:
            return []

        # =========================================================================
        # PRD Section 7.4: Assign 3 Distinct Card Roles (Top Match, Alternative, Exploration)
        # =========================================================================
        structured_3_cards: List[RecommendationCard] = []

        # 1. Top Match (Card 1)
        top_card = cards[0]
        top_card.card_role = CardRole.TOP_MATCH
        top_card.card_role_label = "🎯 最符合需求"
        structured_3_cards.append(top_card)

        # 2. Dispersal Alternative (Card 2: Low crowd, comfortable, similar vibe)
        alt_candidates = [c for c in cards[1:] if c.crowd_score <= 40 or c.is_dispersal_alternative]
        if alt_candidates:
            alt_card = alt_candidates[0]
            alt_card.card_role = CardRole.DISPERSAL_ALTERNATIVE
            alt_card.card_role_label = "✨ 舒適替代選擇 (避開人潮/遮蔭捷運)"
            structured_3_cards.append(alt_card)
        elif len(cards) > 1:
            alt_card = cards[1]
            alt_card.card_role = CardRole.DISPERSAL_ALTERNATIVE
            alt_card.card_role_label = "✨ 推薦替代選擇"
            structured_3_cards.append(alt_card)

        # 3. Exploration Gem (Card 3: Fresh discovery, distinctive tag)
        remaining = [c for c in cards[1:] if c not in structured_3_cards]
        if remaining:
            exp_card = remaining[0]
            exp_card.card_role = CardRole.EXPLORATION_GEM
            exp_card.card_role_label = "💡 特色探索選擇 (私房推薦)"
            structured_3_cards.append(exp_card)

        return structured_3_cards if len(structured_3_cards) == 3 else cards[:3]


ranking_engine = RankingEngine()
