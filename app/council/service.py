"""
app/council/service.py
───────────────────────
Council Builder — selects 4-8 permanent experts most relevant to the query.
Uses an LLM to intelligently pick experts based on domains and domain context.
"""
import json

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import CouncilError
from app.domain.schemas import DomainContext
from app.models.expert import Expert
from app.router.schemas import RouterOutput
from app.services.llm import complete_json


class _CouncilSelection(BaseModel):
    """Internal schema for LLM council selection response."""
    selected_expert_names: list[str]
    selection_reasoning: str


_SYSTEM_PROMPT = """You are the Council Builder for Delphi. Your job is to select the most relevant expert council members from the available pool to evaluate a given decision query.

Select between {min_count} and {max_count} experts. Choose the experts whose domains are most critical for this specific decision. Prioritise depth of relevance over breadth.

Respond ONLY with valid JSON:
{{
  "selected_expert_names": ["Expert Name 1", "Expert Name 2"],
  "selection_reasoning": "Brief explanation of why these experts were selected"
}}"""


async def build_council(
    query: str,
    routing: RouterOutput,
    domain_context: DomainContext,
    db: AsyncSession,
) -> tuple[list[Expert], str]:
    """
    Select the expert council for this case.
    Returns (list of Expert ORM objects, selection_reasoning).
    """
    # Load all active permanent experts from DB
    result = await db.execute(select(Expert).where(Expert.is_active == True))  # noqa: E712
    all_experts = list(result.scalars().all())

    if not all_experts:
        raise CouncilError("No experts found in database. Run expert seeder on startup.")

    expert_pool_desc = "\n".join(
        f"- {e.name} ({e.domain}): {e.description}" for e in all_experts
    )

    target_count = domain_context.recommended_expert_count
    min_count = max(4, target_count - 1)
    max_count = min(8, target_count + 1)

    system = _SYSTEM_PROMPT.format(min_count=min_count, max_count=max_count)
    user_msg = (
        f"Decision Query: {query}\n\n"
        f"Industry: {routing.industry}\n"
        f"Relevant Domains: {', '.join(routing.domains)}\n\n"
        f"Domain Context:\n"
        f"- Key Risks: {', '.join(domain_context.key_risks)}\n"
        f"- Constraints: {', '.join(domain_context.constraints)}\n\n"
        f"Available Experts:\n{expert_pool_desc}"
    )

    selection = await complete_json(
        system=system,
        user=user_msg,
        model=settings.agent_model,
        schema=_CouncilSelection,
        temperature=0.3,
    )

    # Map names back to Expert objects (case-insensitive match for safety)
    expert_map = {e.name.lower(): e for e in all_experts}
    selected = [
        expert_map[name.lower()]
        for name in selection.selected_expert_names
        if name.lower() in expert_map
    ]

    # Fallback: if LLM returned invalid names, pick by domain overlap
    if len(selected) < 4:
        logger.warning("Council selection returned <4 valid experts — using domain fallback")
        domain_set = set(routing.domains)
        selected = [e for e in all_experts if e.domain in domain_set][:6]
        if len(selected) < 4:
            selected = all_experts[:4]

    logger.info(
        f"Council formed: {[e.name for e in selected]} "
        f"({len(selected)} members)"
    )
    return selected, selection.selection_reasoning
