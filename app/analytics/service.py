"""
app/analytics/service.py
────────────────────────
Database service for querying system metrics, leaderboards, timelines, and expert details.
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expert import Expert
from app.models.participation import ExpertParticipation
from app.models.reputation_history import ReputationHistory
from app.models.reflection import Reflection
from app.models.success_pattern import SuccessPattern
from app.models.case import Case


async def get_leaderboard_stats(session: AsyncSession) -> list[dict]:
    """
    Query all experts sorted by reputation score.
    Returns basic ELO rating metrics, case count, average contribution, and last delta.
    """
    stmt = select(Expert).order_by(Expert.reputation_score.desc())
    res = await session.execute(stmt)
    experts = res.scalars().all()

    items = []
    for expert in experts:
        # Calculate case count and average contribution
        part_stmt = (
            select(
                func.count(ExpertParticipation.id),
                func.avg(ExpertParticipation.contribution_score)
            )
            .where(ExpertParticipation.expert_id == expert.id)
            .where(ExpertParticipation.contribution_score.is_not(None))
        )
        part_res = await session.execute(part_stmt)
        case_count, avg_contribution = part_res.fetchone()

        # Get last case ELO delta
        delta_stmt = (
            select(ReputationHistory.change_amount)
            .where(ReputationHistory.expert_id == expert.id)
            .order_by(ReputationHistory.created_at.desc())
            .limit(1)
        )
        delta_res = await session.execute(delta_stmt)
        delta_row = delta_res.fetchone()
        last_delta = delta_row[0] if delta_row else None

        items.append({
            "id": expert.id,
            "name": expert.name,
            "domain": expert.domain,
            "description": expert.description,
            "reputation_score": expert.reputation_score,
            "is_active": expert.is_active,
            "case_count": case_count or 0,
            "avg_contribution": round(avg_contribution, 2) if avg_contribution is not None else None,
            "elo_delta_last_case": last_delta,
        })
    return items


async def get_memory_bank_data(session: AsyncSession) -> dict:
    """
    Fetch all failure reflections and success patterns from previous cases.
    """
    # reflections
    ref_stmt = (
        select(
            Reflection.id,
            Reflection.failure_type,
            Reflection.lesson,
            Reflection.created_at,
            Expert.name.label("expert_name"),
            Expert.domain,
            Case.id.label("case_id"),
            Case.query.label("case_query")
        )
        .join(Expert, Reflection.expert_id == Expert.id)
        .join(Case, Reflection.case_id == Case.id)
        .order_by(Reflection.created_at.desc())
    )
    ref_res = await session.execute(ref_stmt)
    reflections = [
        {
            "id": r.id,
            "expert_name": r.expert_name,
            "domain": r.domain,
            "failure_type": r.failure_type,
            "lesson": r.lesson,
            "case_id": r.case_id,
            "case_query": r.case_query,
            "created_at": r.created_at,
        }
        for r in ref_res.all()
    ]

    # success patterns
    sp_stmt = (
        select(
            SuccessPattern.id,
            SuccessPattern.success_pattern,
            SuccessPattern.created_at,
            Expert.name.label("expert_name"),
            Expert.domain,
            Case.id.label("case_id"),
            Case.query.label("case_query")
        )
        .join(Expert, SuccessPattern.expert_id == Expert.id)
        .join(Case, SuccessPattern.case_id == Case.id)
        .order_by(SuccessPattern.created_at.desc())
    )
    sp_res = await session.execute(sp_stmt)
    success_patterns = [
        {
            "id": s.id,
            "expert_name": s.expert_name,
            "domain": s.domain,
            "success_pattern": s.success_pattern,
            "case_id": s.case_id,
            "case_query": s.case_query,
            "created_at": s.created_at,
        }
        for s in sp_res.all()
    ]

    return {
        "reflections": reflections,
        "success_patterns": success_patterns,
    }


async def get_global_timeline(session: AsyncSession, limit: int = 50) -> list[dict]:
    """
    Fetch a list of recent reputation changes across all experts.
    """
    stmt = (
        select(
            ReputationHistory.id,
            ReputationHistory.reputation_before,
            ReputationHistory.reputation_after,
            ReputationHistory.change_amount,
            ReputationHistory.created_at,
            Expert.name.label("expert_name"),
            Expert.domain,
            Case.id.label("case_id"),
            Case.query.label("case_query")
        )
        .join(Expert, ReputationHistory.expert_id == Expert.id)
        .join(Case, ReputationHistory.case_id == Case.id)
        .order_by(ReputationHistory.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    return [
        {
            "id": r.id,
            "expert_name": r.expert_name,
            "domain": r.domain,
            "case_id": r.case_id,
            "case_query": r.case_query,
            "reputation_before": r.reputation_before,
            "reputation_after": r.reputation_after,
            "change_amount": r.change_amount,
            "created_at": r.created_at,
        }
        for r in res.all()
    ]


async def get_expert_detail_stats(session: AsyncSession, expert_id: str) -> dict | None:
    """
    Fetch comprehensive analytics, metrics, failure distributions,
    and ELO timeline history for a single expert.
    """
    expert = await session.get(Expert, expert_id)
    if not expert:
        return None

    # Query aggregates from participations
    stats_stmt = (
        select(
            func.count(ExpertParticipation.id),
            func.avg(ExpertParticipation.quality_score),
            func.avg(ExpertParticipation.impact_score),
            func.avg(ExpertParticipation.calibration_score),
            func.avg(ExpertParticipation.contribution_score)
        )
        .where(ExpertParticipation.expert_id == expert_id)
        .where(ExpertParticipation.contribution_score.is_not(None))
    )
    stats_res = await session.execute(stats_stmt)
    total_cases, avg_q, avg_i, avg_c, avg_contrib = stats_res.fetchone()

    # Query all case participations
    part_stmt = (
        select(
            ExpertParticipation.case_id,
            ExpertParticipation.role,
            ExpertParticipation.recommendation,
            ExpertParticipation.confidence,
            ExpertParticipation.reasoning,
            ExpertParticipation.quality_score,
            ExpertParticipation.impact_score,
            ExpertParticipation.calibration_score,
            ExpertParticipation.contribution_score,
            ExpertParticipation.self_critique,
            ExpertParticipation.created_at,
            Case.query.label("case_query")
        )
        .join(Case, ExpertParticipation.case_id == Case.id)
        .where(ExpertParticipation.expert_id == expert_id)
        .order_by(ExpertParticipation.created_at.desc())
    )
    part_res = await session.execute(part_stmt)
    participations_list = [
        {
            "case_id": p.case_id,
            "case_query": p.case_query,
            "role": p.role,
            "recommendation": p.recommendation,
            "confidence": p.confidence,
            "reasoning": p.reasoning,
            "quality_score": p.quality_score,
            "impact_score": p.impact_score,
            "calibration_score": p.calibration_score,
            "contribution_score": p.contribution_score,
            "self_critique": p.self_critique,
            "created_at": p.created_at,
        }
        for p in part_res.all()
    ]

    # Failure counts grouped by type
    ref_stmt = (
        select(Reflection.failure_type, func.count(Reflection.id))
        .where(Reflection.expert_id == expert_id)
        .group_by(Reflection.failure_type)
    )
    ref_res = await session.execute(ref_stmt)
    failure_distribution = {row[0]: row[1] for row in ref_res.all()}

    # ELO history sequence (chronological)
    elo_stmt = (
        select(
            ReputationHistory.case_id,
            ReputationHistory.reputation_before,
            ReputationHistory.reputation_after,
            ReputationHistory.change_amount,
            ReputationHistory.created_at,
            Case.query.label("case_query")
        )
        .join(Case, ReputationHistory.case_id == Case.id)
        .where(ReputationHistory.expert_id == expert_id)
        .order_by(ReputationHistory.created_at.asc())
    )
    elo_res = await session.execute(elo_stmt)
    elo_history = [
        {
            "case_id": h.case_id,
            "case_query": h.case_query,
            "reputation_before": h.reputation_before,
            "reputation_after": h.reputation_after,
            "change_amount": h.change_amount,
            "created_at": h.created_at,
        }
        for h in elo_res.all()
    ]

    return {
        "id": expert.id,
        "name": expert.name,
        "domain": expert.domain,
        "description": expert.description,
        "reputation_score": expert.reputation_score,
        "is_active": expert.is_active,
        "total_cases": total_cases or 0,
        "avg_quality_score": round(avg_q, 2) if avg_q is not None else None,
        "avg_impact_score": round(avg_i, 2) if avg_i is not None else None,
        "avg_calibration_score": round(avg_c, 2) if avg_c is not None else None,
        "avg_contribution_score": round(avg_contrib, 2) if avg_contrib is not None else None,
        "failure_distribution": failure_distribution,
        "elo_history": elo_history,
        "participations": participations_list,
    }
