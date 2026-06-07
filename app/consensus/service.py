"""
app/consensus/service.py
─────────────────────────
Consensus Engine — synthesises the full deliberation into a final verdict.
Uses weighted voting (judge overall_score as weight) + LLM synthesis.
"""
import json
from pathlib import Path

from loguru import logger

from app.agents.schemas import ExpertAnalysis
from app.consensus.schemas import ConsensusOutput
from app.core.config import settings
from app.core.exceptions import ConsensusError
from app.debate.schemas import DebateResult
from app.judge.schemas import JudgeRubric
from app.services.llm import complete_json

_CONSENSUS_PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "prompts" / "consensus.md"
)
_CONSENSUS_SYSTEM: str = _CONSENSUS_PROMPT_PATH.read_text(encoding="utf-8")


def _build_deliberation_record(
    query: str,
    debate: DebateResult,
    rubric: JudgeRubric,
) -> str:
    """Combine debate + judge scores into a comprehensive deliberation record."""
    score_map = {s.expert_name.lower(): s for s in rubric.expert_scores}

    sections = [f"Decision Query: {query}\n"]

    for analysis in debate.round1_analyses:
        name_key = analysis.expert_name.lower()
        score = score_map.get(name_key)

        # Find final confidence from rebuttal if available
        rebuttal = next(
            (r for r in debate.round3_rebuttals if r.expert_name.lower() == name_key),
            None,
        )
        final_confidence = rebuttal.updated_confidence if rebuttal else analysis.confidence
        maintained = rebuttal.maintained_position if rebuttal else True

        section = (
            f"--- {analysis.expert_name} ({analysis.domain}) ---\n"
            f"Recommendation: {analysis.recommendation}\n"
            f"Final Confidence: {final_confidence}/100 "
            f"({'maintained' if maintained else 'updated position'})\n"
            f"Reasoning: {analysis.reasoning}\n"
        )

        if rebuttal:
            section += f"Rebuttal Summary: {rebuttal.rebuttal[:200]}...\n"

        if score:
            section += (
                f"Judge Score: {score.overall_score}/10 | "
                f"Feedback: {score.feedback}\n"
            )

        sections.append(section)

    sections.append(
        f"\nJudge Summary:\n"
        f"Strongest: {rubric.strongest_argument}\n"
        f"Weakest: {rubric.weakest_argument}"
    )

    return "\n\n".join(sections)


async def form_consensus(
    query: str,
    debate: DebateResult,
    rubric: JudgeRubric,
) -> ConsensusOutput:
    """
    Produce the final verdict and executive report.
    Uses judge_model for high-quality synthesis.
    """
    logger.info("Consensus engine forming final verdict...")

    deliberation_record = _build_deliberation_record(query, debate, rubric)

    try:
        output = await complete_json(
            system=_CONSENSUS_SYSTEM,
            user=f"Complete Deliberation Record:\n\n{deliberation_record}",
            model=settings.judge_model,
            schema=ConsensusOutput,
            temperature=0.5,
        )
    except Exception as exc:
        raise ConsensusError(f"Consensus formation failed: {exc}") from exc

    # Validate verdict value
    valid_verdicts = {"approve", "reject", "conditional_approve"}
    if output.verdict not in valid_verdicts:
        output.verdict = "conditional_approve"  # Safe default

    # Clamp confidence
    output.confidence = max(0.0, min(100.0, output.confidence))

    logger.info(
        f"Consensus reached — verdict={output.verdict} confidence={output.confidence}"
    )
    return output
