"""
app/api/v1/decisions.py
────────────────────────
Decision API endpoints.

POST /decisions  → Submit a query. Returns case_id immediately.
                   Pipeline runs in background (BackgroundTasks).

GET  /decisions/{case_id} → Poll case status and get result when complete.
"""
import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import CaseNotFoundError
from app.models.case import Case, CaseStatus
from app.services import decision_orchestrator

router = APIRouter(prefix="/decisions", tags=["decisions"])


# ── Request / Response Schemas ────────────────────────────────────────────────

class DecisionRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The decision query to be evaluated by the expert council.",
        examples=["Should we launch a fully autonomous, AI-driven digital banking platform globally?"],
    )
    mock: bool = Field(
        default=False,
        description="Whether to run in simulated/demo mode, bypassing LLM API calls.",
    )


class DecisionSubmitResponse(BaseModel):
    case_id: str
    status: str
    message: str


class DecisionStatusResponse(BaseModel):
    case_id: str
    status: str
    query: str

    # Available once completed
    verdict: str | None = None
    confidence: float | None = None
    council_members: list[str] | None = None
    executive_report: str | None = None

    # Full detail (only when completed)
    full_result: dict | None = None
    error_detail: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=DecisionSubmitResponse, status_code=202)
async def submit_decision(
    request: DecisionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> DecisionSubmitResponse:
    """
    Submit a decision query to the Delphi council.

    Returns a `case_id` immediately (HTTP 202 Accepted).
    Poll `GET /decisions/{case_id}` to check progress and retrieve the result.
    The full pipeline typically takes 20–60 seconds.
    """
    case_id = str(uuid.uuid4())
    case = Case(
        id=case_id,
        query=request.query,
        status=CaseStatus.PENDING,
    )
    db.add(case)
    await db.commit()  # Ensure case is committed before background task starts

    background_tasks.add_task(
        decision_orchestrator.run,
        case_id=case_id,
        query=request.query,
        mock=request.mock,
    )

    return DecisionSubmitResponse(
        case_id=case_id,
        status=CaseStatus.PENDING,
        message=(
            f"Decision query accepted. Your council is being assembled. "
            f"Poll GET /api/v1/decisions/{case_id} to track progress."
        ),
    )


@router.get("/{case_id}", response_model=DecisionStatusResponse)
async def get_decision(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> DecisionStatusResponse:
    """
    Get the current status and result of a decision case.

    Status flow: pending → routing → council_formation → debate → judging → consensus → completed
    If status is `failed`, check `error_detail` for the reason.
    """
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if case is None:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    council_members = None
    if case.council_members:
        try:
            council_members = json.loads(case.council_members)
        except json.JSONDecodeError:
            council_members = []

    full_result = None
    if case.raw_result and case.status == CaseStatus.COMPLETED:
        try:
            full_result = json.loads(case.raw_result)
        except json.JSONDecodeError:
            full_result = None

    return DecisionStatusResponse(
        case_id=case.id,
        status=case.status.value,
        query=case.query,
        verdict=case.verdict.value if case.verdict else None,
        confidence=case.confidence,
        council_members=council_members,
        executive_report=case.executive_report,
        full_result=full_result,
        error_detail=case.error_detail,
    )


@router.get("", response_model=list[DecisionStatusResponse])
async def list_decisions(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> list[DecisionStatusResponse]:
    """List recent decision cases (most recent first)."""
    result = await db.execute(
        select(Case).order_by(Case.created_at.desc()).limit(limit)
    )
    cases = result.scalars().all()

    responses = []
    for case in cases:
        council_members = None
        if case.council_members:
            try:
                council_members = json.loads(case.council_members)
            except json.JSONDecodeError:
                council_members = []

        responses.append(DecisionStatusResponse(
            case_id=case.id,
            status=case.status.value,
            query=case.query,
            verdict=case.verdict.value if case.verdict else None,
            confidence=case.confidence,
            council_members=council_members,
            executive_report=case.executive_report,
            full_result=None,  # Don't return full result in list view
            error_detail=case.error_detail,
        ))

    return responses


@router.get("/{case_id}/stage")
async def get_decision_stage(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return the latest incremental stage snapshot for a case.

    Written after each pipeline step (council, debate, judge, consensus).
    Returns an empty dict if no snapshot has been written yet.
    Allows the frontend to display live data during pipeline execution.
    """
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if case is None:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    if not case.stage_data:
        return {}

    try:
        return json.loads(case.stage_data)
    except json.JSONDecodeError:
        return {}
