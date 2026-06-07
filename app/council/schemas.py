"""app/council/schemas.py — Council builder output schema."""
from pydantic import BaseModel

from app.models.expert import Expert


class CouncilConfig(BaseModel):
    selected_experts: list[str]   # expert names
    expert_count: int
    selection_reasoning: str

    class Config:
        arbitrary_types_allowed = True
