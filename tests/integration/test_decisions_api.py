"""
tests/integration/test_decisions_api.py
──────────────────────────────────────────
Integration tests for POST /decisions and GET /decisions/{case_id}.
LLM calls are mocked — tests verify API contract and DB persistence.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.agents.schemas import ExpertAnalysis, ExpertRebuttal
from app.consensus.schemas import ConsensusOutput
from app.debate.schemas import Challenge, ChallengesResponse, DebateResult
from app.domain.schemas import DomainContext
from app.judge.schemas import ExpertScore, JudgeRubric
from app.router.schemas import RouterOutput

# ── Fixtures / Mocks ──────────────────────────────────────────────────────────

MOCK_ROUTING = RouterOutput(
    industry="healthcare",
    domains=["legal", "security", "technical"],
    complexity="high",
    reasoning="Hospital AI deployment.",
)

MOCK_DOMAIN_CONTEXT = DomainContext(
    industry_context="Healthcare AI is heavily regulated.",
    key_risks=["Patient safety", "Regulatory compliance"],
    constraints=["FDA clearance required"],
    complexity_factors=["High stakes decision"],
    recommended_expert_count=5,
)

MOCK_ANALYSIS = ExpertAnalysis(
    expert_name="Finance Expert",
    domain="finance",
    recommendation="conditional_approve",
    confidence=70.0,
    risks=["High capex"],
    benefits=["Long-term ROI"],
    reasoning="Financially sound with appropriate safeguards.",
    key_assumptions=["Regulatory approval obtained"],
)

MOCK_CHALLENGE_RESP = ChallengesResponse(
    challenges=[
        Challenge(
            expert_name="Finance Expert",
            challenge="Have you considered ongoing maintenance costs?",
            targeted_assumption="Cost estimates are complete",
        )
    ]
)

MOCK_REBUTTAL = ExpertRebuttal(
    expert_name="Finance Expert",
    challenge_received="Have you considered ongoing maintenance costs?",
    rebuttal="Yes, maintenance costs are included in our 5-year TCO.",
    maintained_position=True,
    updated_confidence=68.0,
)

MOCK_RUBRIC = JudgeRubric(
    expert_scores=[
        ExpertScore(
            expert_name="Finance Expert",
            evidence_score=7.0,
            logic_score=7.5,
            consistency_score=7.0,
            rebuttal_quality=7.0,
            overall_score=7.125,
            feedback="Solid analysis with good rebuttal.",
        )
    ],
    strongest_argument="Finance Expert presented coherent analysis.",
    weakest_argument="Finance Expert could improve evidence quality.",
)

MOCK_CONSENSUS = ConsensusOutput(
    verdict="conditional_approve",
    confidence=72.0,
    vote_breakdown={"Finance Expert": "conditional_approve"},
    key_risks=["Regulatory risk"],
    key_benefits=["Patient outcomes improvement"],
    conditions=["Obtain FDA clearance", "Run 3-month pilot"],
    recommendations=["Start with radiology AI", "Establish oversight committee"],
    executive_summary=(
        "The council conditionally approves AI deployment pending FDA clearance. "
        "A structured pilot is recommended before full rollout."
    ),
)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_decision_returns_202(client: AsyncClient) -> None:
    """POST /decisions returns 202 Accepted with a case_id."""
    response = await client.post(
        "/api/v1/decisions",
        json={"query": "Should we deploy AI diagnostics in our hospital ER?"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "case_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_decision_pending(client: AsyncClient) -> None:
    """GET /decisions/{case_id} returns the case while still pending."""
    # Submit first
    post_resp = await client.post(
        "/api/v1/decisions",
        json={"query": "Should we expand our market into Southeast Asia?"},
    )
    case_id = post_resp.json()["case_id"]

    # Immediately poll — should be pending or in-progress
    get_resp = await client.get(f"/api/v1/decisions/{case_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["case_id"] == case_id
    assert data["status"] in (
        "pending", "routing", "council_formation", "debate", "judging", "consensus", "completed", "failed"
    )


@pytest.mark.asyncio
async def test_get_decision_not_found(client: AsyncClient) -> None:
    """GET /decisions/{non_existent_id} returns 404."""
    response = await client.get("/api/v1/decisions/non-existent-id-12345")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_submit_decision_validates_short_query(client: AsyncClient) -> None:
    """POST /decisions rejects queries shorter than 10 characters."""
    response = await client.post(
        "/api/v1/decisions",
        json={"query": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_decisions(client: AsyncClient) -> None:
    """GET /decisions returns a list."""
    response = await client.get("/api/v1/decisions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_decision_stage_empty_initially(client: AsyncClient) -> None:
    """GET /decisions/{case_id}/stage returns 200 and an empty object initially."""
    # Submit first
    post_resp = await client.post(
        "/api/v1/decisions",
        json={"query": "Should we deploy AI diagnostics in our hospital ER?"},
    )
    case_id = post_resp.json()["case_id"]

    # Poll stage endpoint
    response = await client.get(f"/api/v1/decisions/{case_id}/stage")
    assert response.status_code == 200
    assert response.json() == {}


@pytest.mark.asyncio
async def test_get_decision_stage_returns_data(client: AsyncClient, db_session) -> None:
    """GET /decisions/{case_id}/stage returns the stored stage data."""
    from app.models import Case
    import json

    case_id = "test-case-stage-12345"
    stage_data_content = {"routing": {"industry": "healthcare"}, "council": ["Finance Expert"]}
    
    case = Case(
        id=case_id,
        query="Should we deploy AI diagnostics in our hospital ER?",
        status="routing",
        stage_data=json.dumps(stage_data_content),
    )
    db_session.add(case)
    await db_session.flush()

    response = await client.get(f"/api/v1/decisions/{case_id}/stage")
    assert response.status_code == 200
    assert response.json() == stage_data_content


@pytest.mark.asyncio
async def test_get_decision_stage_not_found(client: AsyncClient) -> None:
    """GET /decisions/{non_existent_id}/stage returns 404."""
    response = await client.get("/api/v1/decisions/non-existent-id-12345/stage")
    assert response.status_code == 404

