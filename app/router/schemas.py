"""app/router/schemas.py — Router input/output schemas."""
from pydantic import BaseModel, Field


class RouterOutput(BaseModel):
    industry: str
    domains: list[str]
    complexity: str
    reasoning: str
