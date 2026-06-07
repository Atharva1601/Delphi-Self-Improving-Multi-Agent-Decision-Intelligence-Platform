"""app/debate/schemas.py — Debate round data structures."""
from pydantic import BaseModel

from app.agents.schemas import ExpertAnalysis, ExpertRebuttal


class Challenge(BaseModel):
    expert_name: str
    challenge: str
    targeted_assumption: str


class ChallengesResponse(BaseModel):
    """Wrapper to match judge_challenge.md JSON output."""
    challenges: list[Challenge]


class DebateResult(BaseModel):
    round1_analyses: list[ExpertAnalysis]
    round2_challenges: list[Challenge]
    round3_rebuttals: list[ExpertRebuttal]
