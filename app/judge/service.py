"""
app/judge/service.py
────────────────────
Judge — evaluates the complete debate and scores each expert.
Uses the powerful judge_model for thorough evaluation.
"""
from pathlib import Path

from loguru import logger

from app.core.config import settings
from app.core.exceptions import JudgeError
from app.debate.schemas import DebateResult
from app.judge.schemas import JudgeRubric
from app.services.llm import complete_json

_RUBRIC_PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "prompts" / "judge_rubric.md"
)
_RUBRIC_SYSTEM: str = _RUBRIC_PROMPT_PATH.read_text(encoding="utf-8")


def _format_debate_record(debate: DebateResult) -> str:
    """Format the full debate into a readable record for the judge."""
    # Build a lookup for challenges and rebuttals
    challenge_map = {c.expert_name.lower(): c for c in debate.round2_challenges}
    rebuttal_map = {r.expert_name.lower(): r for r in debate.round3_rebuttals}

    sections = []
    for analysis in debate.round1_analyses:
        name_key = analysis.expert_name.lower()
        challenge = challenge_map.get(name_key)
        rebuttal = rebuttal_map.get(name_key)

        section = (
            f"=== {analysis.expert_name} ({analysis.domain}) ===\n\n"
            f"[ROUND 1 — INITIAL ANALYSIS]\n"
            f"Recommendation: {analysis.recommendation}\n"
            f"Confidence: {analysis.confidence}/100\n"
            f"Reasoning: {analysis.reasoning}\n"
            f"Risks: {', '.join(analysis.risks)}\n"
            f"Benefits: {', '.join(analysis.benefits)}\n"
            f"Key Assumptions: {', '.join(analysis.key_assumptions)}\n\n"
        )

        if challenge:
            section += (
                f"[ROUND 2 — JUDGE'S CHALLENGE]\n"
                f"{challenge.challenge}\n"
                f"(Targeting assumption: {challenge.targeted_assumption})\n\n"
            )

        if rebuttal:
            section += (
                f"[ROUND 3 — EXPERT REBUTTAL]\n"
                f"{rebuttal.rebuttal}\n"
                f"Maintained Position: {rebuttal.maintained_position}\n"
                f"Updated Confidence: {rebuttal.updated_confidence}/100\n"
            )

        sections.append(section)

    return "\n\n".join(sections)


async def evaluate_debate(debate: DebateResult, debate_enabled: bool = True) -> JudgeRubric:
    """
    Score each expert's full debate performance.
    Uses judge_model (llama-3.3-70b) for thorough evaluation.
    """
    logger.info("Judge evaluating debate — scoring all participants...")

    debate_record = _format_debate_record(debate)

    user_prompt = f"Full Debate Record:\n\n{debate_record}"
    if not debate_enabled:
        user_prompt += (
            "\n\nNote: This is a Non-Debate evaluation. Only Round 1 independent analyses "
            "were conducted; no challenges or rebuttals were performed. Please evaluate "
            "the initial analyses. Since there are no rebuttals, you MUST score "
            "'rebuttal_quality' identical to 'logic_score' for each expert."
        )

    try:
        rubric = await complete_json(
            system=_RUBRIC_SYSTEM,
            user=user_prompt,
            model=settings.judge_model,
            schema=JudgeRubric,
            temperature=0.4,  # Low temp for consistent scoring
        )
    except Exception as exc:
        raise JudgeError(f"Debate evaluation failed: {exc}") from exc

    # Recompute overall_score to ensure correctness
    for score in rubric.expert_scores:
        score.overall_score = round(
            (score.evidence_score + score.logic_score +
             score.consistency_score + score.rebuttal_quality) / 4,
            2,
        )

    logger.info(
        f"Judge evaluation complete — "
        f"strongest={rubric.strongest_argument[:50]}..."
    )
    return rubric
