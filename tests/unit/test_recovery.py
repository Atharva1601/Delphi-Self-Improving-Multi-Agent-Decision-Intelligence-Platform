"""
tests/unit/test_recovery.py
───────────────────────────
Unit tests for the Delphi Recovery Mode (Phase 5).
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.expert import Expert
from app.models.case import Case, CaseStatus
from app.models.participation import ExpertParticipation, ParticipationRole
from app.reflection.service import (
    get_expert_recent_average_contribution,
    is_expert_in_recovery,
)
from app.agents.expert import analyze as expert_analyze
from app.debate.schemas import ExpertAnalysis
from app.domain.schemas import DomainContext
from app.reputation.service import process_reputation_updates


@pytest.mark.asyncio
async def test_recovery_trigger_averages(db_session: AsyncSession):
    """Verify that rolling contribution averages are correctly calculated."""
    expert = Expert(name="Test Expert", domain="finance")
    db_session.add(expert)
    await db_session.flush()

    case1 = Case(query="Q1", status=CaseStatus.COMPLETED)
    case2 = Case(query="Q2", status=CaseStatus.COMPLETED)
    db_session.add_all([case1, case2])
    await db_session.flush()

    # 1. Less than 2 cases should return None
    avg_one = await get_expert_recent_average_contribution(db_session, expert.id)
    assert avg_one is None
    assert await is_expert_in_recovery(db_session, expert.id) is False

    # Add 1 participation
    part1 = ExpertParticipation(
        expert_id=expert.id,
        case_id=case1.id,
        role=ParticipationRole.COUNCIL_MEMBER,
        contribution_score=85.0,
    )
    db_session.add(part1)
    await db_session.flush()

    avg_still_one = await get_expert_recent_average_contribution(db_session, expert.id)
    assert avg_still_one is None
    assert await is_expert_in_recovery(db_session, expert.id) is False

    # Add 2nd participation (average = (85 + 65) / 2 = 75.0)
    part2 = ExpertParticipation(
        expert_id=expert.id,
        case_id=case2.id,
        role=ParticipationRole.COUNCIL_MEMBER,
        contribution_score=65.0,
    )
    db_session.add(part2)
    await db_session.flush()

    avg_two = await get_expert_recent_average_contribution(db_session, expert.id)
    assert avg_two == 75.0
    # Average of 75.0 is >= 70.0 (threshold), so NOT in recovery
    assert await is_expert_in_recovery(db_session, expert.id) is False

    # Add 3rd participation with a low score (average of last 2 (since lookback=5 and we have 3): (85 + 65 + 50) / 3 = 66.67)
    case3 = Case(query="Q3", status=CaseStatus.COMPLETED)
    db_session.add(case3)
    await db_session.flush()

    part3 = ExpertParticipation(
        expert_id=expert.id,
        case_id=case3.id,
        role=ParticipationRole.COUNCIL_MEMBER,
        contribution_score=50.0,
    )
    db_session.add(part3)
    await db_session.flush()

    avg_three = await get_expert_recent_average_contribution(db_session, expert.id)
    assert round(avg_three, 2) == 66.67
    # 66.67 < 70.0, should trigger recovery mode
    assert await is_expert_in_recovery(db_session, expert.id) is True


@pytest.mark.asyncio
async def test_recovery_briefing_prompt_injection(db_session: AsyncSession):
    """Verify that the expert analysis prompt contains self-critique instructions in recovery."""
    expert = Expert(name="Finance Expert", domain="finance")
    
    with patch("app.agents.expert.complete_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = ExpertAnalysis(
            expert_name="Finance Expert",
            domain="finance",
            recommendation="approve",
            confidence=80.0,
            risks=[],
            benefits=[],
            reasoning="Reasoning test.",
            key_assumptions=[],
            self_critique="My critique of past failures."
        )

        domain_ctx = DomainContext(
            industry_context="Test Context",
            key_risks=[],
            constraints=[],
            complexity_factors=[],
            recommended_expert_count=3,
        )

        # 1. Normal state (is_recovery = False)
        await expert_analyze(
            query="Should we expand?",
            domain_context=domain_ctx,
            expert=expert,
            is_recovery=False,
        )
        _, kwargs = mock_llm.call_args
        system_prompt_normal = kwargs["system"]
        assert "RECOVERY MODE: Self-Critique Required" not in system_prompt_normal

        # 2. Recovery state (is_recovery = True)
        await expert_analyze(
            query="Should we expand?",
            domain_context=domain_ctx,
            expert=expert,
            is_recovery=True,
        )
        _, kwargs = mock_llm.call_args
        system_prompt_recovery = kwargs["system"]
        assert "RECOVERY MODE: Self-Critique Required" in system_prompt_recovery


@pytest.mark.asyncio
async def test_self_critique_database_persistence(db_session: AsyncSession):
    """Verify that self_critique is correctly saved to ExpertParticipation."""
    expert = Expert(name="Finance Expert", domain="finance")
    db_session.add(expert)
    await db_session.flush()

    case = Case(query="Should we build a platform?", status=CaseStatus.CONSENSUS)
    db_session.add(case)
    await db_session.flush()

    analyses = [
        {
            "expert_name": "Finance Expert",
            "domain": "finance",
            "recommendation": "approve",
            "confidence": 85.0,
            "risks": [],
            "benefits": [],
            "reasoning": "Standard reasoning.",
            "key_assumptions": [],
            "self_critique": "Self-critique about previous database limits.",
        }
    ]
    rebuttals = [
        {
            "expert_name": "Finance Expert",
            "rebuttal": "Standard rebuttal.",
            "updated_confidence": 85.0,
        }
    ]
    expert_scores = [
        {
            "expert_name": "Finance Expert",
            "evidence_score": 8.0,
            "logic_score": 8.0,
            "consistency_score": 8.0,
            "rebuttal_quality": 8.0,
            "overall_score": 8.0,
        }
    ]

    # Run the transaction directly passing session=db_session
    await process_reputation_updates(
        case_id=case.id,
        analyses=analyses,
        rebuttals=rebuttals,
        expert_scores=expert_scores,
        strongest_argument="None",
        weakest_argument="None",
        consensus_verdict="approve",
        session=db_session,
    )
    await db_session.flush()

    # Query participation and assert self_critique was saved
    stmt = select(ExpertParticipation).where(ExpertParticipation.case_id == case.id)
    res = await db_session.execute(stmt)
    participation = res.scalar_one()
    
    assert participation.self_critique == "Self-critique about previous database limits."


@pytest.mark.asyncio
async def test_elo_based_recovery_trigger(db_session: AsyncSession):
    """Verify that ELO score dropping below the ELO threshold triggers recovery mode."""
    # 1. Expert with ELO above threshold (1000 ELO) -> not in recovery
    expert_high = Expert(name="Expert High", domain="finance", reputation_score=1000.0)
    db_session.add(expert_high)
    await db_session.flush()
    assert await is_expert_in_recovery(db_session, expert_high.id) is False

    # 2. Expert with ELO below threshold (940 ELO < 950.0) -> in recovery
    expert_low = Expert(name="Expert Low", domain="security", reputation_score=940.0)
    db_session.add(expert_low)
    await db_session.flush()
    assert await is_expert_in_recovery(db_session, expert_low.id) is True
