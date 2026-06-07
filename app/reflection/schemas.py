"""
app/reflection/schemas.py
──────────────────────────
Pydantic schemas for the Court Stenographer (Clerk) Agent output.
"""
from pydantic import BaseModel, Field


class ReflectionOutput(BaseModel):
    expert_name: str = Field(..., description="Exact expert name as specified in target briefing.")
    failure_type: str = Field(..., description="One of: weak_evidence | logical_flaw | poor_calibration | inconsistent_position | generic_analysis | other")
    lesson: str = Field(..., description="Constructive lesson explaining what they did wrong and how to fix it.")


class SuccessPatternOutput(BaseModel):
    expert_name: str = Field(..., description="Exact expert name as specified in target briefing.")
    success_pattern: str = Field(..., description="Detailed description of what made their performance successful.")


class ClerkOutput(BaseModel):
    reflections: list[ReflectionOutput] = Field(default_factory=list, description="Reflections for experts with Contribution Score < threshold.")
    success_patterns: list[SuccessPatternOutput] = Field(default_factory=list, description="Success patterns for experts with Contribution Score > threshold.")
