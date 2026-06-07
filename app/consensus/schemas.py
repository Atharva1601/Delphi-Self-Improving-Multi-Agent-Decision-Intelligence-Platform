"""app/consensus/schemas.py — Consensus engine output schema."""
from pydantic import BaseModel


class ConsensusOutput(BaseModel):
    verdict: str                          # approve | reject | conditional_approve
    confidence: float                     # 0–100
    vote_breakdown: dict[str, str]        # expert_name → recommendation
    key_risks: list[str]
    key_benefits: list[str]
    conditions: list[str]                 # conditions for conditional_approve
    recommendations: list[str]
    executive_summary: str
