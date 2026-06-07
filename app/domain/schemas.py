"""app/domain/schemas.py — Domain specialist output schema."""
from pydantic import BaseModel


class DomainContext(BaseModel):
    industry_context: str
    key_risks: list[str]
    constraints: list[str]
    complexity_factors: list[str]
    recommended_expert_count: int
