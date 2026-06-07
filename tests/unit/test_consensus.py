"""
tests/unit/test_consensus.py
──────────────────────────────
Unit tests for the Consensus Engine (mocked LLM).
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.agents.schemas import ExpertAnalysis, ExpertRebuttal
from app.consensus.schemas import ConsensusOutput
from app.consensus.service import form_consensus
from app.debate.schemas import Challenge, DebateResult
from app.judge.schemas import ExpertScore, JudgeRubric


def _make_debate_result() -> DebateResult:
    analyses = [
        ExpertAnalysis(
            expert_name="Finance Expert",
            domain="finance",
            recommendation="approve",
            confidence=75.0,
            risks=["High capex"],
            benefits=["Long-term ROI"],
            reasoning="Strong financial case exists.",
            key_assumptions=["Market conditions stable"],
        ),
        ExpertAnalysis(
            expert_name="Legal Expert",
            domain="legal",
            recommendation="conditional_approve",
            confidence=60.0,
            risks=["Regulatory approval needed"],
            benefits=["Compliance opportunity"],
            reasoning="Conditional on FDA clearance.",
            key_assumptions=["Regulations don't change"],
        ),
    ]
    challenges = [
        Challenge(
            expert_name="Finance Expert",
            challenge="Have you accounted for hidden integration costs?",
            targeted_assumption="Cost estimates are accurate",
        ),
    ]
    rebuttals = [
        ExpertRebuttal(
            expert_name="Finance Expert",
            challenge_received="Have you accounted for hidden integration costs?",
            rebuttal="Integration costs are included in our TCO model.",
            maintained_position=True,
            updated_confidence=72.0,
        ),
    ]
    return DebateResult(
        round1_analyses=analyses,
        round2_challenges=challenges,
        round3_rebuttals=rebuttals,
    )


def _make_rubric() -> JudgeRubric:
    return JudgeRubric(
        expert_scores=[
            ExpertScore(
                expert_name="Finance Expert",
                evidence_score=7.0,
                logic_score=8.0,
                consistency_score=7.5,
                rebuttal_quality=7.0,
                overall_score=7.375,
                feedback="Solid financial analysis.",
            ),
            ExpertScore(
                expert_name="Legal Expert",
                evidence_score=6.0,
                logic_score=7.0,
                consistency_score=6.5,
                rebuttal_quality=6.0,
                overall_score=6.375,
                feedback="Good regulatory awareness.",
            ),
        ],
        strongest_argument="Finance Expert made the strongest case.",
        weakest_argument="Legal Expert could be more specific.",
    )


MOCK_CONSENSUS = ConsensusOutput(
    verdict="conditional_approve",
    confidence=70.0,
    vote_breakdown={"Finance Expert": "approve", "Legal Expert": "conditional_approve"},
    key_risks=["Regulatory risk"],
    key_benefits=["Strong ROI"],
    conditions=["Obtain FDA clearance"],
    recommendations=["Pilot program first"],
    executive_summary="The council recommends conditional approval pending FDA clearance.",
)


@pytest.mark.asyncio
async def test_consensus_returns_valid_verdict():
    """Consensus must return approve, reject, or conditional_approve."""
    with patch("app.consensus.service.complete_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_CONSENSUS
        result = await form_consensus(
            "Deploy AI diagnostics?",
            _make_debate_result(),
            _make_rubric(),
        )

    assert result.verdict in ("approve", "reject", "conditional_approve")


@pytest.mark.asyncio
async def test_consensus_clamps_confidence():
    """Confidence must always be 0–100 even if model returns out-of-range value."""
    bad_consensus = MOCK_CONSENSUS.model_copy(update={"confidence": 150.0})
    with patch("app.consensus.service.complete_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = bad_consensus
        result = await form_consensus(
            "Deploy AI diagnostics?",
            _make_debate_result(),
            _make_rubric(),
        )

    assert 0.0 <= result.confidence <= 100.0


@pytest.mark.asyncio
async def test_consensus_uses_judge_model():
    """Consensus must use the judge_model for high-quality synthesis."""
    from app.core.config import settings

    with patch("app.consensus.service.complete_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_CONSENSUS
        await form_consensus("Test query", _make_debate_result(), _make_rubric())

    call_kwargs = mock_llm.call_args.kwargs
    assert call_kwargs["model"] == settings.judge_model
