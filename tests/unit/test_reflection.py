"""
tests/unit/test_reflection.py
──────────────────────────────
Unit tests for the Delphi Reflection Engine (Phase 4).
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.expert import Expert
from app.models.case import Case, CaseStatus
from app.models.reflection import Reflection
from app.models.success_pattern import SuccessPattern
from app.debate.schemas import DebateResult, Challenge, ExpertAnalysis, ExpertRebuttal
from app.judge.schemas import ExpertScore, JudgeRubric
from app.reflection.schemas import ClerkOutput, ReflectionOutput, SuccessPatternOutput
from app.reflection.service import (
    get_domain_lessons,
    format_past_lessons,
    format_debate_transcript,
    format_judge_rubric,
    format_targets_briefing,
    run_reflection_engine,
)


def test_format_past_lessons():
    """Verify past lessons format correctly as markdown list or empty string."""
    # Empty
    assert format_past_lessons([], []) == ""

    # Reflections only
    res = format_past_lessons(["[logical_flaw] Avoid bias."], [])
    assert "## Past Lessons Learned for Domain Roles" in res
    assert "### Failure Pitfalls to Avoid:" in res
    assert "- [logical_flaw] Avoid bias." in res
    assert "### Successful Strategies to Exhibit:" not in res

    # Success patterns only
    res = format_past_lessons([], ["Cite concrete API specs."])
    assert "## Past Lessons Learned for Domain Roles" in res
    assert "### Successful Strategies to Exhibit:" in res
    assert "- Cite concrete API specs." in res
    assert "### Failure Pitfalls to Avoid:" not in res

    # Both
    res = format_past_lessons(["[logical_flaw] Avoid bias."], ["Cite concrete API specs."])
    assert "- [logical_flaw] Avoid bias." in res
    assert "- Cite concrete API specs." in res


def test_format_debate_transcript():
    """Verify debate transcript formats nicely for the Clerk agent."""
    debate_result = DebateResult(
        round1_analyses=[
            ExpertAnalysis(
                expert_name="Finance Expert",
                domain="finance",
                recommendation="approve",
                confidence=90.0,
                risks=["cap"],
                benefits=["roi"],
                reasoning="Reasoning finance.",
                key_assumptions=["ok"],
            )
        ],
        round2_challenges=[
            Challenge(
                expert_name="Finance Expert",
                challenge="Is it safe?",
                targeted_assumption="ok",
            )
        ],
        round3_rebuttals=[
            ExpertRebuttal(
                expert_name="Finance Expert",
                challenge_received="Is it safe?",
                rebuttal="Yes it is safe.",
                maintained_position=True,
                updated_confidence=90.0,
            )
        ],
    )

    transcript = format_debate_transcript(debate_result)
    assert "=== Round 1: Independent Analysis ===" in transcript
    assert "Expert: Finance Expert" in transcript
    assert "Reasoning: Reasoning finance." in transcript
    assert "=== Round 2: Judge Challenges ===" in transcript
    assert "Challenge: Is it safe?" in transcript
    assert "=== Round 3: Expert Rebuttals ===" in transcript
    assert "Rebuttal: Yes it is safe." in transcript


def test_format_judge_rubric():
    """Verify judge rubric formats correctly."""
    rubric = JudgeRubric(
        expert_scores=[
            ExpertScore(
                expert_name="Finance Expert",
                evidence_score=8.0,
                logic_score=8.5,
                consistency_score=8.0,
                rebuttal_quality=8.5,
                overall_score=8.25,
                feedback="Good job.",
            )
        ],
        avg_evidence_quality=8.0,
        avg_logic_score=8.5,
        avg_consistency_score=8.0,
        avg_rebuttal_quality=8.5,
        overall_quality_score=8.25,
        strongest_argument="Finance expert evidence was strong.",
        weakest_argument="None.",
    )

    rubric_str = format_judge_rubric(rubric)
    assert "=== Expert Rubric Scores ===" in rubric_str
    assert "Expert: Finance Expert" in rubric_str
    assert "Scores: Evidence=8.0, Logic=8.5" in rubric_str
    assert "Strongest Argument: Finance expert evidence was strong." in rubric_str


def test_format_targets_briefing():
    """Verify targets briefing maps experts to the correct categories based on score."""
    updates = [
        {"expert_name": "Finance Expert", "contribution_score": 50.0},
        {"expert_name": "Legal Expert", "contribution_score": 85.0},
        {"expert_name": "Security Expert", "contribution_score": 70.0},
    ]

    briefing = format_targets_briefing(
        updates,
        failure_threshold=60.0,
        success_threshold=80.0,
    )
    assert "Finance Expert: Contribution Score = 50.0. Requires Reflection Lesson" in briefing
    assert "Legal Expert: Contribution Score = 85.0. Requires Success Pattern" in briefing
    assert "Security Expert: Contribution Score = 70.0. Within baseline range" in briefing


@pytest.mark.asyncio
async def test_get_domain_lessons_from_db(db_session: AsyncSession):
    """Verify get_domain_lessons correctly queries and formats historical entries."""
    expert = Expert(
        name="Finance Specialist",
        domain="finance",
        reputation_score=1000.0,
    )
    db_session.add(expert)
    await db_session.flush()

    case = Case(
        query="Should we invest in crypto?",
        status=CaseStatus.COMPLETED,
    )
    db_session.add(case)
    await db_session.flush()

    ref = Reflection(
        expert_id=expert.id,
        case_id=case.id,
        failure_type="poor_calibration",
        lesson="Calibrate better next time.",
    )
    pat = SuccessPattern(
        expert_id=expert.id,
        case_id=case.id,
        success_pattern="Structured evidence works well.",
    )
    db_session.add_all([ref, pat])
    await db_session.flush()

    reflections, success_patterns = await get_domain_lessons(
        session=db_session,
        domain="finance",
        limit=3,
    )

    assert len(reflections) == 1
    assert reflections[0] == "[poor_calibration] Calibrate better next time."
    assert len(success_patterns) == 1
    assert success_patterns[0] == "Structured evidence works well."

    # Non-existent domain
    reflections_none, success_patterns_none = await get_domain_lessons(
        session=db_session,
        domain="non-existent",
        limit=3,
    )
    assert len(reflections_none) == 0
    assert len(success_patterns_none) == 0


@pytest.mark.asyncio
async def test_run_reflection_engine_persists(db_session: AsyncSession):
    """Verify run_reflection_engine calls Clerk and persists reflections/success patterns."""
    expert_a = Expert(name="Finance Expert", domain="finance")
    expert_b = Expert(name="Legal Expert", domain="legal")
    db_session.add_all([expert_a, expert_b])
    await db_session.flush()

    case = Case(query="Should we expand market?", status=CaseStatus.CONSENSUS)
    db_session.add(case)
    await db_session.flush()

    debate_result = DebateResult(
        round1_analyses=[],
        round2_challenges=[],
        round3_rebuttals=[],
    )
    rubric = JudgeRubric(
        expert_scores=[],
        avg_evidence_quality=8.0,
        avg_logic_score=8.0,
        avg_consistency_score=8.0,
        avg_rebuttal_quality=8.0,
        overall_quality_score=8.0,
        strongest_argument="None",
        weakest_argument="None",
    )

    # Updates where Finance Expert failed and Legal Expert succeeded
    reputation_updates = [
        {"expert_name": "Finance Expert", "contribution_score": 45.0},
        {"expert_name": "Legal Expert", "contribution_score": 88.0},
    ]

    mock_clerk_output = ClerkOutput(
        reflections=[
            ReflectionOutput(
                expert_name="Finance Expert",
                failure_type="generic_analysis",
                lesson="Cite specific interest rates.",
            )
        ],
        success_patterns=[
            SuccessPatternOutput(
                expert_name="Legal Expert",
                success_pattern="Structured regulatory timelines.",
            )
        ],
    )

    # Mock the LLM call to return the ClerkOutput
    with patch("app.reflection.service.complete_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_clerk_output

        result = await run_reflection_engine(
            case_id=case.id,
            query=case.query,
            debate_result=debate_result,
            rubric=rubric,
            reputation_updates=reputation_updates,
            session=db_session,
        )
        await db_session.flush()

        assert len(result["reflections"]) == 1
        assert len(result["success_patterns"]) == 1
        assert result["reflections"][0]["expert_name"] == "Finance Expert"
        assert result["success_patterns"][0]["expert_name"] == "Legal Expert"

        # Verify DB entries
        ref_db = await db_session.execute(
            select(Reflection).where(Reflection.case_id == case.id)
        )
        reflections = list(ref_db.scalars().all())
        assert len(reflections) == 1
        assert reflections[0].failure_type == "generic_analysis"
        assert reflections[0].lesson == "Cite specific interest rates."
        assert reflections[0].expert_id == expert_a.id

        pat_db = await db_session.execute(
            select(SuccessPattern).where(SuccessPattern.case_id == case.id)
        )
        patterns = list(pat_db.scalars().all())
        assert len(patterns) == 1
        assert patterns[0].success_pattern == "Structured regulatory timelines."
        assert patterns[0].expert_id == expert_b.id
