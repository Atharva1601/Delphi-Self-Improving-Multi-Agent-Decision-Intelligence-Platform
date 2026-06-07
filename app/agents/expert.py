"""
app/agents/expert.py
─────────────────────
Expert Agent — performs independent analysis and rebuttals.
All council members are called in parallel via asyncio.gather().
"""
import json
from pathlib import Path

from loguru import logger

from app.agents.schemas import ExpertAnalysis, ExpertRebuttal
from app.core.config import settings
from app.core.exceptions import AgentError
from app.domain.schemas import DomainContext
from app.models.expert import Expert
from app.services.llm import complete_json

_ANALYSIS_PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "prompts" / "expert_analysis.md"
)
_ANALYSIS_TEMPLATE: str = _ANALYSIS_PROMPT_PATH.read_text(encoding="utf-8")

_REBUTTAL_SYSTEM = """You are {expert_name}, a senior {domain} expert on the Delphi decision council. You have received a challenge to your initial analysis. Respond thoughtfully.

Respond ONLY with valid JSON:
{{
  "expert_name": "{expert_name}",
  "challenge_received": "the challenge you received",
  "rebuttal": "Your detailed rebuttal — defend your position or acknowledge the valid point and update your view (3+ sentences)",
  "maintained_position": true,
  "updated_confidence": 75.0
}}

Rules:
- maintained_position is true if your recommendation is unchanged, false if you are updating it
- updated_confidence is your new confidence (0-100) after considering the challenge
- Be intellectually honest — if the challenge revealed a valid gap, acknowledge it
- rebuttal must be at least 3 sentences"""


async def analyze(
    query: str,
    domain_context: DomainContext,
    expert: Expert,
    past_reflections: list[str] | None = None,
    past_success_patterns: list[str] | None = None,
    is_recovery: bool = False,
) -> ExpertAnalysis:
    """
    Run one expert's independent analysis (Round 1).
    Called in parallel for all council members.
    """
    from app.reflection.service import format_past_lessons

    domain_ctx_str = (
        f"Industry Context: {domain_context.industry_context}\n"
        f"Key Risks: {', '.join(domain_context.key_risks)}\n"
        f"Constraints: {', '.join(domain_context.constraints)}"
    )

    past_lessons_str = format_past_lessons(
        reflections=past_reflections or [],
        success_patterns=past_success_patterns or [],
    )

    if is_recovery:
        recovery_str = (
            "## RECOVERY MODE: Self-Critique Required\n"
            "Your recent domain contributions have fallen below performance baselines. "
            "You MUST perform a self-critique of your past failure patterns (listed below) "
            "and outline how you are correcting your analysis for the current query to avoid repeating them. "
            "Populate this in the \"self_critique\" field in your JSON output (minimum 2 sentences)."
        )
    else:
        recovery_str = ""

    system = (
        _ANALYSIS_TEMPLATE
        .replace("{expert_name}", expert.name)
        .replace("{domain}", expert.domain)
        .replace("{past_lessons_section}", past_lessons_str)
        .replace("{recovery_section}", recovery_str)
    )

    user_msg = (
        f"Decision Query:\n{query}\n\n"
        f"Domain Briefing:\n{domain_ctx_str}"
    )

    try:
        result = await complete_json(
            system=system,
            user=user_msg,
            model=settings.agent_model,
            schema=ExpertAnalysis,
            temperature=0.7,
        )
        # Ensure expert_name matches DB record
        result.expert_name = expert.name
        result.domain = expert.domain
        logger.debug(
            f"{expert.name} → {result.recommendation} (confidence={result.confidence})"
        )
        return result
    except Exception as exc:
        raise AgentError(
            f"{expert.name} analysis failed: {exc}",
            detail={"expert": expert.name},
        ) from exc


async def rebut(
    analysis: ExpertAnalysis,
    challenge: str,
    expert: Expert,
) -> ExpertRebuttal:
    """
    Expert responds to the judge's challenge (Round 3).
    Called in parallel for all council members.
    """
    system = _REBUTTAL_SYSTEM.format(
        expert_name=expert.name,
        domain=expert.domain,
    )

    user_msg = (
        f"Your original analysis:\n"
        f"Recommendation: {analysis.recommendation}\n"
        f"Confidence: {analysis.confidence}\n"
        f"Reasoning: {analysis.reasoning}\n"
        f"Key Assumptions: {', '.join(analysis.key_assumptions)}\n\n"
        f"Judge's Challenge:\n{challenge}"
    )

    try:
        result = await complete_json(
            system=system,
            user=user_msg,
            model=settings.agent_model,
            schema=ExpertRebuttal,
            temperature=0.6,
        )
        result.expert_name = expert.name
        result.challenge_received = challenge
        logger.debug(
            f"{expert.name} rebuttal — maintained={result.maintained_position} "
            f"updated_confidence={result.updated_confidence}"
        )
        return result
    except Exception as exc:
        raise AgentError(
            f"{expert.name} rebuttal failed: {exc}",
            detail={"expert": expert.name},
        ) from exc
