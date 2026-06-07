"""
app/analytics/schemas.py
────────────────────────
Pydantic validation and serialization schemas for Phase 6 Admin Dashboard.
"""
from datetime import datetime
from pydantic import BaseModel


class ExpertLeaderboardItem(BaseModel):
    id: str
    name: str
    domain: str
    description: str | None
    reputation_score: float
    is_active: bool
    case_count: int
    avg_contribution: float | None
    elo_delta_last_case: float | None


class ReflectionListItem(BaseModel):
    id: str
    expert_name: str
    domain: str
    failure_type: str
    lesson: str
    case_id: str
    case_query: str
    created_at: datetime


class SuccessPatternListItem(BaseModel):
    id: str
    expert_name: str
    domain: str
    success_pattern: str
    case_id: str
    case_query: str
    created_at: datetime


class MemoryBankResponse(BaseModel):
    reflections: list[ReflectionListItem]
    success_patterns: list[SuccessPatternListItem]


class TimelineItem(BaseModel):
    id: str
    expert_name: str
    domain: str
    case_id: str
    case_query: str
    reputation_before: float
    reputation_after: float
    change_amount: float
    created_at: datetime


class ExpertTimelineItem(BaseModel):
    case_id: str
    case_query: str
    reputation_before: float
    reputation_after: float
    change_amount: float
    created_at: datetime


class ExpertParticipationItem(BaseModel):
    case_id: str
    case_query: str
    role: str
    recommendation: str | None
    confidence: float | None
    reasoning: str | None
    quality_score: float | None
    impact_score: float | None
    calibration_score: float | None
    contribution_score: float | None
    self_critique: str | None
    created_at: datetime


class ExpertDetailResponse(BaseModel):
    id: str
    name: str
    domain: str
    description: str | None
    reputation_score: float
    is_active: bool
    total_cases: int
    avg_quality_score: float | None
    avg_impact_score: float | None
    avg_calibration_score: float | None
    avg_contribution_score: float | None
    failure_distribution: dict[str, int]
    elo_history: list[ExpertTimelineItem]
    participations: list[ExpertParticipationItem]
