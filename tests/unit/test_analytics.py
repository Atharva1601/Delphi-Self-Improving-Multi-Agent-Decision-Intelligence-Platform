"""
tests/unit/test_analytics.py
────────────────────────────
Unit and integration tests for the Delphi Observability Analytics Dashboard (Phase 6).
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expert import Expert
from app.models.case import Case, CaseStatus
from app.models.participation import ExpertParticipation, ParticipationRole
from app.models.reputation_history import ReputationHistory
from app.models.reflection import Reflection
from app.models.success_pattern import SuccessPattern
from app.analytics import service as analytics_service


async def seed_analytics_data(db: AsyncSession):
    """Seed DB with a full suite of experts, cases, participations, and memory items."""
    from sqlalchemy import delete

    # Clear existing tables to prevent UNIQUE constraint failures from lifespan seeding
    await db.execute(delete(Reflection))
    await db.execute(delete(SuccessPattern))
    await db.execute(delete(ExpertParticipation))
    await db.execute(delete(ReputationHistory))
    await db.execute(delete(Case))
    await db.execute(delete(Expert))
    await db.commit()

    # 1. Seed Experts
    expert_a = Expert(
        id="expert-1",
        name="Finance Expert",
        domain="finance",
        description="Handles monetary policies",
        reputation_score=1100.0,
        is_active=True,
    )
    expert_b = Expert(
        id="expert-2",
        name="Security Expert",
        domain="security",
        description="Cybersecurity compliance officer",
        reputation_score=950.0,
        is_active=True,
    )
    expert_c = Expert(
        id="expert-3",
        name="Legal Expert",
        domain="legal",
        description="Contracts and corporate governance",
        reputation_score=1000.0,
        is_active=True,
    )
    db.add_all([expert_a, expert_b, expert_c])
    await db.commit()

    # 2. Seed Cases
    case_1 = Case(
        id="case-1",
        query="Should we invest $2M in cyber security infrastructure?",
        status=CaseStatus.COMPLETED,
    )
    case_2 = Case(
        id="case-2",
        query="Can we launch the fintech product in Europe next quarter?",
        status=CaseStatus.COMPLETED,
    )
    db.add_all([case_1, case_2])
    await db.commit()

    # 3. Seed Participations
    # Finance Expert in case 1 and 2
    part_1 = ExpertParticipation(
        id="part-1",
        expert_id="expert-1",
        case_id="case-1",
        role=ParticipationRole.COUNCIL_MEMBER,
        recommendation="approve",
        confidence=90.0,
        reasoning="Strong financial ROI.",
        quality_score=80.0,
        impact_score=70.0,
        calibration_score=90.0,
        contribution_score=79.0, # 0.5*80 + 0.3*70 + 0.2*90 = 40+21+18 = 79
    )
    part_2 = ExpertParticipation(
        id="part-2",
        expert_id="expert-1",
        case_id="case-2",
        role=ParticipationRole.COUNCIL_MEMBER,
        recommendation="approve",
        confidence=80.0,
        reasoning="Europe fintech is viable.",
        quality_score=90.0,
        impact_score=80.0,
        calibration_score=80.0,
        contribution_score=85.0,
    )
    # Security Expert in case 1 (low contribution, triggers reflection)
    part_3 = ExpertParticipation(
        id="part-3",
        expert_id="expert-2",
        case_id="case-1",
        role=ParticipationRole.COUNCIL_MEMBER,
        recommendation="reject",
        confidence=95.0,
        reasoning="Critical security flaws.",
        quality_score=50.0,
        impact_score=50.0,
        calibration_score=40.0,
        contribution_score=48.0, # low score, below 70 -> recovery/reflection
        self_critique="I over-indexed on marginal vulnerabilities.",
    )
    db.add_all([part_1, part_2, part_3])
    await db.commit()

    # 4. Seed Reputation Histories
    rh_1 = ReputationHistory(
        id="rh-1",
        expert_id="expert-1",
        case_id="case-1",
        reputation_before=1080.0,
        reputation_after=1100.0,
        change_amount=20.0,
        council_average_rating=1000.0,
    )
    rh_2 = ReputationHistory(
        id="rh-2",
        expert_id="expert-2",
        case_id="case-1",
        reputation_before=980.0,
        reputation_after=950.0,
        change_amount=-30.0,
        council_average_rating=1000.0,
    )
    db.add_all([rh_1, rh_2])
    await db.commit()

    # 5. Seed Memory Bank items (Reflections & Success Patterns)
    ref_1 = Reflection(
        id="ref-1",
        expert_id="expert-2",
        case_id="case-1",
        failure_type="alert_fatigue",
        lesson="Calibrate warning priorities to prevent false positives.",
    )
    sp_1 = SuccessPattern(
        id="sp-1",
        expert_id="expert-1",
        case_id="case-2",
        success_pattern="Leveraged strict ROI checklists to guide council consensus.",
    )
    db.add_all([ref_1, sp_1])
    await db.commit()


@pytest.mark.asyncio
async def test_get_leaderboard_stats(db_session: AsyncSession):
    """Verify leaderboard stats are sorted correctly by reputation score with correct case counts."""
    await seed_analytics_data(db_session)

    stats = await analytics_service.get_leaderboard_stats(db_session)
    assert len(stats) == 3

    # Assert sort order (expert-1 has 1100, expert-3 has 1000, expert-2 has 950)
    assert stats[0]["id"] == "expert-1"
    assert stats[1]["id"] == "expert-3"
    assert stats[2]["id"] == "expert-2"

    # Expert-1 detailed assertions
    expert_1_data = stats[0]
    assert expert_1_data["case_count"] == 2
    assert expert_1_data["avg_contribution"] == 82.0 # (79.0 + 85.0) / 2 = 82.0
    assert expert_1_data["elo_delta_last_case"] == 20.0

    # Expert-3 (no participations) assertions
    expert_3_data = stats[1]
    assert expert_3_data["case_count"] == 0
    assert expert_3_data["avg_contribution"] is None
    assert expert_3_data["elo_delta_last_case"] is None


@pytest.mark.asyncio
async def test_get_memory_bank_data(db_session: AsyncSession):
    """Verify that memory bank data fetches reflections and success patterns with joins."""
    await seed_analytics_data(db_session)

    bank = await analytics_service.get_memory_bank_data(db_session)
    assert "reflections" in bank
    assert "success_patterns" in bank

    assert len(bank["reflections"]) == 1
    assert bank["reflections"][0]["expert_name"] == "Security Expert"
    assert bank["reflections"][0]["failure_type"] == "alert_fatigue"
    assert bank["reflections"][0]["lesson"] == "Calibrate warning priorities to prevent false positives."

    assert len(bank["success_patterns"]) == 1
    assert bank["success_patterns"][0]["expert_name"] == "Finance Expert"
    assert bank["success_patterns"][0]["success_pattern"] == "Leveraged strict ROI checklists to guide council consensus."


@pytest.mark.asyncio
async def test_get_global_timeline(db_session: AsyncSession):
    """Verify reputation history timeline logs returns all items chronologically."""
    await seed_analytics_data(db_session)

    timeline = await analytics_service.get_global_timeline(db_session, limit=10)
    # Both logs (rh_1 and rh_2) should be returned
    assert len(timeline) == 2
    # Since rh-1 and rh-2 are created around same time, we check their joined details
    experts = [item["expert_name"] for item in timeline]
    assert "Finance Expert" in experts
    assert "Security Expert" in experts
    assert timeline[0]["case_query"] == "Should we invest $2M in cyber security infrastructure?"


@pytest.mark.asyncio
async def test_get_expert_detail_stats(db_session: AsyncSession):
    """Verify detailed analytics return profile, aggregates, breakdown, and timeline history."""
    await seed_analytics_data(db_session)

    # 1. Expert with history details
    detail_1 = await analytics_service.get_expert_detail_stats(db_session, "expert-1")
    assert detail_1 is not None
    assert detail_1["name"] == "Finance Expert"
    assert detail_1["total_cases"] == 2
    assert detail_1["avg_quality_score"] == 85.0 # (80+90)/2
    assert detail_1["avg_contribution_score"] == 82.0 # (79+85)/2
    assert len(detail_1["elo_history"]) == 1
    assert detail_1["elo_history"][0]["change_amount"] == 20.0
    assert len(detail_1["participations"]) == 2

    # 2. Expert with low performance / reflection breakdown
    detail_2 = await analytics_service.get_expert_detail_stats(db_session, "expert-2")
    assert detail_2 is not None
    assert detail_2["total_cases"] == 1
    assert detail_2["avg_contribution_score"] == 48.0
    assert detail_2["failure_distribution"] == {"alert_fatigue": 1}
    assert detail_2["participations"][0]["self_critique"] == "I over-indexed on marginal vulnerabilities."

    # 3. Non-existent expert
    detail_missing = await analytics_service.get_expert_detail_stats(db_session, "missing-id")
    assert detail_missing is None


@pytest.mark.asyncio
async def test_analytics_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    """Verify FastAPI routes output data matches Pydantic schemas validation."""
    await seed_analytics_data(db_session)

    # Test GET /api/v1/analytics/leaderboard
    response = await client.get("/api/v1/analytics/leaderboard")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["name"] == "Finance Expert"
    assert data[0]["reputation_score"] == 1100.0

    # Test GET /api/v1/analytics/memory-bank
    response = await client.get("/api/v1/analytics/memory-bank")
    assert response.status_code == 200
    data = response.json()
    assert len(data["reflections"]) == 1
    assert len(data["success_patterns"]) == 1
    assert data["reflections"][0]["failure_type"] == "alert_fatigue"

    # Test GET /api/v1/analytics/timeline
    response = await client.get("/api/v1/analytics/timeline")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["change_amount"] in [20.0, -30.0]

    # Test GET /api/v1/analytics/experts/{expert_id}
    response = await client.get("/api/v1/analytics/experts/expert-1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Finance Expert"
    assert data["total_cases"] == 2
    assert len(data["elo_history"]) == 1
    assert len(data["participations"]) == 2

    # Test GET /api/v1/analytics/experts/{expert_id} - 404 Case
    response = await client.get("/api/v1/analytics/experts/non-existent")
    assert response.status_code == 404
