"""
app/debate/service.py
──────────────────────
Debate Orchestrator — runs the 3-round structured debate.

Round 1: Parallel expert analysis        (asyncio.gather)
Round 2: Judge generates one challenge per expert
Round 3: Parallel expert rebuttals       (asyncio.gather)
"""
import asyncio
import json
from pathlib import Path

from loguru import logger

from app.agents import expert as expert_agent
from app.agents.schemas import ExpertAnalysis, ExpertRebuttal
from app.core.config import settings
from app.core.exceptions import DebateError
from app.debate.schemas import Challenge, ChallengesResponse, DebateResult
from app.domain.schemas import DomainContext
from app.models.expert import Expert
from app.services.llm import complete_json

_CHALLENGE_PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "prompts" / "judge_challenge.md"
)
_CHALLENGE_SYSTEM: str = _CHALLENGE_PROMPT_PATH.read_text(encoding="utf-8")


def _format_analyses_for_judge(analyses: list[ExpertAnalysis]) -> str:
    parts = []
    for a in analyses:
        parts.append(
            f"--- {a.expert_name} ({a.domain}) ---\n"
            f"Recommendation: {a.recommendation}\n"
            f"Confidence: {a.confidence}/100\n"
            f"Reasoning: {a.reasoning}\n"
            f"Key Assumptions: {', '.join(a.key_assumptions)}\n"
            f"Risks: {', '.join(a.risks)}\n"
            f"Benefits: {', '.join(a.benefits)}"
        )
    return "\n\n".join(parts)


async def run_debate(
    query: str,
    domain_context: DomainContext,
    council: list[Expert],
    expert_lessons: dict[str, tuple[list[str], list[str]]] | None = None,
    recovery_status: dict[str, bool] | None = None,
    debate: bool = True,
) -> DebateResult:
    """
    Execute the full 3-round debate and return the complete DebateResult.
    """
    # ── Round 1: Parallel independent analysis ─────────────────────────────
    logger.info(f"Debate Round 1 — {len(council)} experts analysing in parallel...")
    
    def get_lessons_for_expert(expert_id: str):
        if expert_lessons and expert_id in expert_lessons:
            return expert_lessons[expert_id]
        return [], []

    def get_recovery_status(expert_id: str) -> bool:
        if recovery_status and expert_id in recovery_status:
            return recovery_status[expert_id]
        return False

    try:
        analyses: list[ExpertAnalysis] = await asyncio.gather(
            *[
                expert_agent.analyze(
                    query,
                    domain_context,
                    e,
                    past_reflections=get_lessons_for_expert(e.id)[0],
                    past_success_patterns=get_lessons_for_expert(e.id)[1],
                    is_recovery=get_recovery_status(e.id),
                )
                for e in council
            ]
        )
    except Exception as exc:
        raise DebateError(f"Round 1 failed: {exc}") from exc

    logger.info("Round 1 complete.")

    if not debate:
        logger.info("Debate is disabled (no-debate mode). Skipping Round 2 challenges and Round 3 rebuttals.")
        return DebateResult(
            round1_analyses=list(analyses),
            round2_challenges=[],
            round3_rebuttals=[],
        )

    # ── Round 2: Judge generates challenges ────────────────────────────────
    logger.info("Debate Round 2 — Judge generating challenges...")
    analyses_text = _format_analyses_for_judge(analyses)
    try:
        challenges_resp = await complete_json(
            system=_CHALLENGE_SYSTEM,
            user=f"Expert Analyses:\n\n{analyses_text}",
            model=settings.judge_model,
            schema=ChallengesResponse,
            temperature=0.6,
        )
        challenges = challenges_resp.challenges
    except Exception as exc:
        raise DebateError(f"Round 2 challenge generation failed: {exc}") from exc

    # Build challenge lookup by expert name
    challenge_map: dict[str, str] = {
        c.expert_name.lower(): c.challenge for c in challenges
    }

    logger.info(f"Round 2 complete — {len(challenges)} challenges issued.")

    # ── Round 3: Parallel rebuttals ────────────────────────────────────────
    logger.info("Debate Round 3 — Experts rebutting in parallel...")

    async def _rebuttal_task(analysis: ExpertAnalysis, exp: Expert) -> ExpertRebuttal:
        challenge_text = challenge_map.get(
            exp.name.lower(),
            "Defend the overall soundness of your recommendation with additional supporting evidence.",
        )
        return await expert_agent.rebut(analysis, challenge_text, exp)

    try:
        rebuttals: list[ExpertRebuttal] = await asyncio.gather(
            *[_rebuttal_task(a, e) for a, e in zip(analyses, council)]
        )
    except Exception as exc:
        raise DebateError(f"Round 3 rebuttal failed: {exc}") from exc

    logger.info("Round 3 complete — all rebuttals received.")

    return DebateResult(
        round1_analyses=list(analyses),
        round2_challenges=challenges,
        round3_rebuttals=list(rebuttals),
    )
