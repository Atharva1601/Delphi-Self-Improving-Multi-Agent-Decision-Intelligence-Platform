"""app/judge/schemas.py — Judge rubric schemas."""
from pydantic import BaseModel


class ExpertScore(BaseModel):
    expert_name: str
    evidence_score: float
    logic_score: float
    consistency_score: float
    rebuttal_quality: float
    overall_score: float
    feedback: str


class JudgeRubric(BaseModel):
    expert_scores: list[ExpertScore]
    strongest_argument: str
    weakest_argument: str
