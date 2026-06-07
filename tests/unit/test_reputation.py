"""
tests/unit/test_reputation.py
──────────────────────────────
Unit and integration tests for the Delphi Reputation Engine (Phase 3).
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.expert import Expert
from app.models.participation import ExpertParticipation, ParticipationRole
from app.models.reputation_history import ReputationHistory
from app.reputation.service import (
    calculate_quality_score,
    calculate_impact_score,
    calculate_calibration_score,
    calculate_contribution_score,
    calculate_elo_delta,
    apply_reputation_update,
    process_reputation_updates,
)


def test_quality_score_calculation():
    """Verify quality score is mapped from 0-10 to 0-100 scale."""
    assert calculate_quality_score(8.5) == 85.0
    assert calculate_quality_score(10.0) == 100.0
    assert calculate_quality_score(0.0) == 0.0


def test_impact_score_calculation():
    """Verify impact score accounts for strongest/weakest citations properly."""
    # Base = 50.0
    assert calculate_impact_score("Finance Expert", "Finance Expert is strongest", "Legal Expert") == 80.0
    assert calculate_impact_score("Legal Expert", "Finance Expert", "Legal Expert is weakest") == 30.0
    assert calculate_impact_score("Product Strategy Expert", "Finance Expert", "Legal Expert") == 50.0

    # Test clamping
    # If someone was strongest but name matches weakest too? Clamping will prevent overflow
    assert calculate_impact_score("Finance Expert", "", "") == 50.0


def test_calibration_score_calculation():
    """
    Verify calibration score behaves correctly.
    - confidence = 90, quality = 90 -> score = 100
    - confidence = 90, quality = 30 -> score = 40
    """
    # Perfect calibration
    assert calculate_calibration_score(90.0, 90.0) == 100.0
    # Poor calibration
    assert calculate_calibration_score(90.0, 30.0) == 40.0
    assert calculate_calibration_score(30.0, 90.0) == 40.0


def test_contribution_formula():
    """Verify contribution score matches formula: 0.5*Q + 0.3*I + 0.2*C."""
    # Q=80, I=50, C=90 -> 0.5*80 + 0.3*50 + 0.2*90 = 40 + 15 + 18 = 73
    assert calculate_contribution_score(80.0, 50.0, 90.0) == 73.0


def test_reputation_bounds():
    """Verify reputation updates never cross MIN_REPUTATION and MAX_REPUTATION."""
    # Current = 1290, delta = 20 -> Clamps to MAX_REPUTATION (1300)
    assert apply_reputation_update(1290.0, 20.0) == settings.max_reputation
    # Current = 710, delta = -20 -> Clamps to MIN_REPUTATION (700)
    assert apply_reputation_update(710.0, -20.0) == settings.min_reputation


def test_underdog_reputation_gain():
    """
    Verify that an underdog receives a larger rating gain than a favorite
    for the same contribution score.
    """
    # Expert A (Favorite): 1200
    # Expert B (Underdog): 800
    # Avg = 1000
    # Contribution score = 80.0 (A = 0.8)
    avg_rating = 1000.0
    contrib = 80.0

    delta_fav = calculate_elo_delta(
        current_rating=1200.0,
        council_average_rating=avg_rating,
        contribution_score=contrib,
    )
    delta_und = calculate_elo_delta(
        current_rating=800.0,
        council_average_rating=avg_rating,
        contribution_score=contrib,
    )

    # Underdog should gain more reputation
    assert delta_und > delta_fav


@pytest.mark.asyncio
async def test_process_reputation_updates_commits_to_db(db_session: AsyncSession):
    """
    Verify process_reputation_updates correctly persists updates,
    ExpertParticipations, and ReputationHistory to the DB.
    """
    # Setup: insert a test Case and two test Experts
    from app.models.case import Case, CaseStatus

    test_case = Case(
        query="Should we invest in cyber insurance?",
        status=CaseStatus.JUDGING,
    )
    db_session.add(test_case)

    expert_a = Expert(
        name="Security Expert",
        domain="security",
        reputation_score=1000.0,
    )
    expert_b = Expert(
        name="Finance Expert",
        domain="finance",
        reputation_score=1000.0,
    )
    db_session.add_all([expert_a, expert_b])
    await db_session.commit()

    # Inputs representing the outcome of a case
    analyses = [
        {"expert_name": "Security Expert", "recommendation": "approve", "confidence": 90.0, "reasoning": "SecReason"},
        {"expert_name": "Finance Expert", "recommendation": "approve", "confidence": 80.0, "reasoning": "FinReason"},
    ]
    rebuttals = [
        {"expert_name": "Security Expert", "updated_confidence": 95.0, "maintained_position": True},
        {"expert_name": "Finance Expert", "updated_confidence": 80.0, "maintained_position": True},
    ]
    expert_scores = [
        {"expert_name": "Security Expert", "overall_score": 9.0}, # quality = 90
        {"expert_name": "Finance Expert", "overall_score": 7.0},  # quality = 70
    ]

    # Run the transaction
    await process_reputation_updates(
        case_id=test_case.id,
        analyses=analyses,
        rebuttals=rebuttals,
        expert_scores=expert_scores,
        strongest_argument="Security Expert provided the best security advice.",
        weakest_argument="Finance Expert argument was standard.",
        consensus_verdict="approve",
        session=db_session,
    )

    # Flush changes to DB and refresh experts
    await db_session.flush()
    await db_session.refresh(expert_a)
    await db_session.refresh(expert_b)
    exp_a_db = expert_a
    exp_b_db = expert_b

    # Reputation should have changed
    assert exp_a_db.reputation_score != 1000.0
    assert exp_b_db.reputation_score != 1000.0

    # Check ExpertParticipation entries
    parts_res = await db_session.execute(
        select(ExpertParticipation).where(ExpertParticipation.case_id == test_case.id)
    )
    participations = list(parts_res.scalars().all())
    assert len(participations) == 2

    sec_part = next(p for p in participations if p.expert_id == expert_a.id)
    assert sec_part.quality_score == 90.0  # 9.0 * 10
    assert sec_part.impact_score == 80.0   # 50 + 30 (strongest)
    assert sec_part.calibration_score == 95.0 # 100 - abs(95 - 90)
    assert sec_part.contribution_score == (0.5 * 90.0 + 0.3 * 80.0 + 0.2 * 95.0)

    # Check ReputationHistory logs
    history_res = await db_session.execute(
        select(ReputationHistory).where(ReputationHistory.case_id == test_case.id)
    )
    history = list(history_res.scalars().all())
    assert len(history) == 2
    assert any(h.expert_id == expert_a.id for h in history)
    assert any(h.expert_id == expert_b.id for h in history)
    assert all(h.council_average_rating == 1000.0 for h in history)


@pytest.mark.asyncio
async def test_calculate_simulated_reputation_updates():
    """
    Verify calculate_simulated_reputation_updates correctly computes ratings
    without writing anything to the database.
    """
    from app.reputation.service import calculate_simulated_reputation_updates
    
    analyses = [
        {"expert_name": "Simulated Security Expert", "recommendation": "approve", "confidence": 90.0, "reasoning": "SecReason"},
        {"expert_name": "Simulated Finance Expert", "recommendation": "approve", "confidence": 80.0, "reasoning": "FinReason"},
    ]
    rebuttals = [
        {"expert_name": "Simulated Security Expert", "updated_confidence": 95.0, "maintained_position": True},
        {"expert_name": "Simulated Finance Expert", "updated_confidence": 80.0, "maintained_position": True},
    ]
    expert_scores = [
        {"expert_name": "Simulated Security Expert", "overall_score": 9.0}, # quality = 90
        {"expert_name": "Simulated Finance Expert", "overall_score": 7.0},  # quality = 70
    ]

    updates = await calculate_simulated_reputation_updates(
        analyses=analyses,
        rebuttals=rebuttals,
        expert_scores=expert_scores,
        strongest_argument="Simulated Security Expert provided the best security advice.",
        weakest_argument="Simulated Finance Expert argument was standard.",
    )

    assert len(updates) == 2
    sec_update = next(u for u in updates if u["expert_name"] == "Simulated Security Expert")
    assert sec_update["quality_score"] == 90.0
    assert sec_update["impact_score"] == 80.0
    assert sec_update["calibration_score"] == 95.0
    assert sec_update["reputation_before"] == 1000.0
    assert sec_update["reputation_after"] > 1000.0
    assert sec_update["change_amount"] > 0

