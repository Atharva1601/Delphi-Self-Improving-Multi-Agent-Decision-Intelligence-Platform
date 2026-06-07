"""app/agents/schemas.py — Expert agent input/output schemas."""
from pydantic import BaseModel


class ExpertAnalysis(BaseModel):
    expert_name: str
    domain: str
    recommendation: str          # approve | reject | conditional_approve
    confidence: float            # 0–100
    risks: list[str]
    benefits: list[str]
    reasoning: str
    key_assumptions: list[str]
    self_critique: str | None = None


class ExpertRebuttal(BaseModel):
    expert_name: str
    challenge_received: str
    rebuttal: str
    maintained_position: bool
    updated_confidence: float    # 0–100
