"""
app/domain/service.py
─────────────────────
Domain Specialist — produces industry context, risks, and constraints.
No reputation, no reflection — pure contextual intelligence.
"""
from pathlib import Path

from loguru import logger

from app.core.config import settings
from app.domain.schemas import DomainContext
from app.router.schemas import RouterOutput
from app.services.llm import complete_json

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "domain_specialist.md"
_SYSTEM_PROMPT: str = _PROMPT_PATH.read_text(encoding="utf-8")


async def get_domain_context(query: str, routing: RouterOutput) -> DomainContext:
    """
    Generate a structured domain briefing for the expert council.
    """
    logger.info(f"Domain specialist analysing: industry={routing.industry}")

    user_msg = (
        f"Decision Query:\n{query}\n\n"
        f"Industry: {routing.industry}\n"
        f"Relevant Domains: {', '.join(routing.domains)}\n"
        f"Complexity: {routing.complexity}\n\n"
        f"Routing Reasoning: {routing.reasoning}"
    )

    context = await complete_json(
        system=_SYSTEM_PROMPT,
        user=user_msg,
        model=settings.agent_model,
        schema=DomainContext,
        temperature=0.5,
    )

    # Clamp recommended expert count to valid range
    context.recommended_expert_count = max(4, min(8, context.recommended_expert_count))

    logger.info(
        f"Domain context ready — risks={len(context.key_risks)} "
        f"recommended_experts={context.recommended_expert_count}"
    )
    return context
