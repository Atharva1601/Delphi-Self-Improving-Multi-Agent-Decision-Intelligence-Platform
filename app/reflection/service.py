"""
app/reflection/service.py
──────────────────────────
Reflection Engine Service — manages retrieving past domain lessons/success patterns,
formatting prompt briefings, running the Court Stenographer (Clerk) Agent,
and persisting reflections/success patterns.
"""
from pathlib import Path
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.expert import Expert
from app.models.reflection import Reflection
from app.models.success_pattern import SuccessPattern
from app.reflection.schemas import ClerkOutput
from app.services.llm import complete_json


async def get_domain_lessons(
    session: AsyncSession,
    domain: str,
    limit: int = 3,
) -> tuple[list[str], list[str]]:
    """
    Retrieve the latest reflections (failure lessons) and success patterns for a domain.
    Returns a tuple of (list of reflection strings, list of success pattern strings).
    """
    # 1. Retrieve reflections
    ref_stmt = (
        select(Reflection.failure_type, Reflection.lesson)
        .join(Expert, Reflection.expert_id == Expert.id)
        .where(Expert.domain == domain)
        .order_by(Reflection.created_at.desc())
        .limit(limit)
    )
    ref_res = await session.execute(ref_stmt)
    reflections = [f"[{r.failure_type}] {r.lesson}" for r in ref_res.all()]

    # 2. Retrieve success patterns
    sp_stmt = (
        select(SuccessPattern.success_pattern)
        .join(Expert, SuccessPattern.expert_id == Expert.id)
        .where(Expert.domain == domain)
        .order_by(SuccessPattern.created_at.desc())
        .limit(limit)
    )
    sp_res = await session.execute(sp_stmt)
    success_patterns = list(sp_res.scalars().all())

    return reflections, success_patterns


async def get_expert_recent_average_contribution(
    session: AsyncSession,
    expert_id: str,
    lookback: int = 5,
) -> float | None:
    """
    Fetch the average contribution score for the last `lookback` cases the expert participated in.
    Returns the average score or None if they haven't completed enough cases (minimum 2).
    """
    from app.models.participation import ExpertParticipation

    stmt = (
        select(ExpertParticipation.contribution_score)
        .where(ExpertParticipation.expert_id == expert_id)
        .where(ExpertParticipation.contribution_score.is_not(None))
        .order_by(ExpertParticipation.created_at.desc())
        .limit(lookback)
    )
    res = await session.execute(stmt)
    scores = [r[0] for r in res.all()]

    if len(scores) < 2:
        return None

    return sum(scores) / len(scores)


async def is_expert_in_recovery(
    session: AsyncSession,
    expert_id: str,
) -> bool:
    """
    Check if the expert's recent contribution score average is below recovery_threshold,
    OR if their current ELO reputation score falls below the reputation recovery threshold.
    """
    expert = await session.get(Expert, expert_id)
    if expert and expert.reputation_score < settings.reputation_recovery_threshold:
        return True

    avg = await get_expert_recent_average_contribution(
        session=session,
        expert_id=expert_id,
        lookback=settings.recovery_lookback,
    )
    if avg is None:
        return False

    return avg < settings.recovery_threshold



def format_past_lessons(reflections: list[str], success_patterns: list[str]) -> str:
    """Format past lessons and success patterns into markdown injection block."""
    if not reflections and not success_patterns:
        return ""

    parts = ["## Past Lessons Learned for Domain Roles"]
    parts.append(
        "To adapt and improve your analysis, review these past lessons and success "
        "patterns from previous deliberations in your domain:"
    )

    if reflections:
        parts.append("### Failure Pitfalls to Avoid:")
        for ref in reflections:
            parts.append(f"- {ref}")

    if success_patterns:
        parts.append("### Successful Strategies to Exhibit:")
        for sp in success_patterns:
            parts.append(f"- {sp}")

    return "\n".join(parts)


def format_debate_transcript(debate_result) -> str:
    """Format the full 3-round debate transcript for the Clerk agent review."""
    transcript = []

    transcript.append("=== Round 1: Independent Analysis ===")
    for analysis in debate_result.round1_analyses:
        transcript.append(
            f"Expert: {analysis.expert_name}\n"
            f"Recommendation: {analysis.recommendation}\n"
            f"Confidence: {analysis.confidence}\n"
            f"Reasoning: {analysis.reasoning}\n"
            f"Assumptions: {', '.join(analysis.key_assumptions)}\n"
            f"Risks: {', '.join(analysis.risks)}\n"
            f"Benefits: {', '.join(analysis.benefits)}\n"
        )

    transcript.append("=== Round 2: Judge Challenges ===")
    for challenge in debate_result.round2_challenges:
        transcript.append(
            f"Target: {challenge.expert_name}\n"
            f"Challenge: {challenge.challenge}\n"
            f"Targeted Assumption: {challenge.targeted_assumption}\n"
        )

    transcript.append("=== Round 3: Expert Rebuttals ===")
    for rebuttal in debate_result.round3_rebuttals:
        transcript.append(
            f"Expert: {rebuttal.expert_name}\n"
            f"Rebuttal: {rebuttal.rebuttal}\n"
            f"Maintained Position: {rebuttal.maintained_position}\n"
            f"Updated Confidence: {rebuttal.updated_confidence}\n"
        )

    return "\n".join(transcript)


def format_judge_rubric(rubric) -> str:
    """Format the Judge Rubric for the Clerk agent review."""
    parts = []
    parts.append("=== Expert Rubric Scores ===")
    for score in rubric.expert_scores:
        parts.append(
            f"Expert: {score.expert_name}\n"
            f"Scores: Evidence={score.evidence_score}, Logic={score.logic_score}, "
            f"Consistency={score.consistency_score}, Rebuttal={score.rebuttal_quality}, "
            f"Overall={score.overall_score}\n"
            f"Feedback: {score.feedback}\n"
        )
    parts.append(f"Strongest Argument: {rubric.strongest_argument}")
    parts.append(f"Weakest Argument: {rubric.weakest_argument}")
    return "\n".join(parts)


def format_targets_briefing(
    reputation_updates: list[dict],
    failure_threshold: float,
    success_threshold: float,
) -> str:
    """Format contribution score targets list for Clerk review briefing."""
    lines = []
    for update in reputation_updates:
        score = update["contribution_score"]
        name = update["expert_name"]
        if score < failure_threshold:
            lines.append(
                f"- {name}: Contribution Score = {score:.1f}. Requires Reflection Lesson (Failure)."
            )
        elif score > success_threshold:
            lines.append(
                f"- {name}: Contribution Score = {score:.1f}. Requires Success Pattern."
            )
        else:
            lines.append(
                f"- {name}: Contribution Score = {score:.1f}. Within baseline range, no action needed."
            )
    return "\n".join(lines)


async def run_reflection_engine(
    case_id: str,
    query: str,
    debate_result,
    rubric,
    reputation_updates: list[dict],
    session: AsyncSession,
) -> dict:
    """
    Evaluates thresholds, runs Clerk Agent (if applicable),
    and persists generated reflections/success patterns to the database.
    """
    failure_thresh = settings.reflection_failure_threshold
    success_thresh = settings.reflection_success_threshold

    # Check if anyone qualified
    targets = []
    for update in reputation_updates:
        score = update["contribution_score"]
        name = update["expert_name"]
        if score < failure_thresh:
            targets.append((name, "reflection", score))
        elif score > success_thresh:
            targets.append((name, "success_pattern", score))

    if not targets:
        logger.info("No experts qualified for reflection or success pattern generation.")
        return {"reflections": [], "success_patterns": []}

    logger.info(f"Qualifying experts for Clerk review: {targets}")

    # Build the Clerk Prompt
    debate_transcript = format_debate_transcript(debate_result)
    judge_rubric_formatted = format_judge_rubric(rubric)
    targets_briefing = format_targets_briefing(reputation_updates, failure_thresh, success_thresh)

    prompt_path = (
        Path(__file__).parent.parent.parent
        / "prompts"
        / "clerk_stenographer.md"
    )
    system_prompt = prompt_path.read_text(encoding="utf-8")

    system_prompt = (
        system_prompt.replace("{query}", query)
        .replace("{debate_transcript}", debate_transcript)
        .replace("{judge_rubric}", judge_rubric_formatted)
        .replace("{targets_briefing}", targets_briefing)
    )

    try:
        # Run Clerk Agent (using settings.agent_model or settings.judge_model)
        # Using settings.judge_model because Clerk requires structured evaluation logic
        clerk_resp = await complete_json(
            system=system_prompt,
            user=(
                "Impartially record the courtroom proceedings and generate "
                "the reflections and success patterns in JSON format."
            ),
            model=settings.judge_model,
            schema=ClerkOutput,
            temperature=0.4,
        )
    except Exception as exc:
        logger.error(f"Clerk agent completion failed: {exc}")
        return {"reflections": [], "success_patterns": []}

    # Save to database
    expert_names = [r.expert_name for r in clerk_resp.reflections] + [
        s.expert_name for s in clerk_resp.success_patterns
    ]
    db_experts = {}
    if expert_names:
        stmt = select(Expert).where(Expert.name.in_(expert_names))
        res = await session.execute(stmt)
        db_experts = {e.name.lower(): e for e in res.scalars().all()}

    saved_reflections = []
    saved_patterns = []

    for r in clerk_resp.reflections:
        expert = db_experts.get(r.expert_name.lower())
        if expert:
            reflection_obj = Reflection(
                expert_id=expert.id,
                case_id=case_id,
                failure_type=r.failure_type,
                lesson=r.lesson,
            )
            session.add(reflection_obj)
            saved_reflections.append(
                {
                    "expert_name": expert.name,
                    "failure_type": r.failure_type,
                    "lesson": r.lesson,
                }
            )
        else:
            logger.warning(
                f"Clerk generated reflection for expert '{r.expert_name}' but expert was not found in DB."
            )

    for s in clerk_resp.success_patterns:
        expert = db_experts.get(s.expert_name.lower())
        if expert:
            pattern_obj = SuccessPattern(
                expert_id=expert.id,
                case_id=case_id,
                success_pattern=s.success_pattern,
            )
            session.add(pattern_obj)
            saved_patterns.append(
                {
                    "expert_name": expert.name,
                    "success_pattern": s.success_pattern,
                }
            )
        else:
            logger.warning(
                f"Clerk generated success pattern for expert '{s.expert_name}' but expert was not found in DB."
            )

    logger.info(
        f"Clerk persisted {len(saved_reflections)} reflections and {len(saved_patterns)} success patterns."
    )

    return {
        "reflections": saved_reflections,
        "success_patterns": saved_patterns,
    }
