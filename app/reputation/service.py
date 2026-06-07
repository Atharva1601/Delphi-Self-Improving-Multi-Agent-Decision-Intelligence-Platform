"""
app/reputation/service.py
─────────────────────────
Reputation engine service containing scoring and rating update functions.
"""
from loguru import logger
from sqlalchemy import select

from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.models.expert import Expert
from app.models.participation import ExpertParticipation, ParticipationRole
from app.models.reputation_history import ReputationHistory


def calculate_quality_score(judge_score: float) -> float:
    """Return quality score scaled from 0-10 judge score to 0-100."""
    return judge_score * 10.0


def calculate_impact_score(
    expert_name: str,
    strongest_argument: str,
    weakest_argument: str,
) -> float:
    """Return impact score based on judge's strongest/weakest argument citations."""
    impact_score = 50.0

    if expert_name.lower() in strongest_argument.lower():
        impact_score += 30.0

    if expert_name.lower() in weakest_argument.lower():
        impact_score -= 20.0

    return max(0.0, min(100.0, impact_score))


def calculate_calibration_score(confidence: float, quality_score: float) -> float:
    """Return calibration score based on confidence and quality deviation."""
    return max(0.0, 100.0 - abs(confidence - quality_score))


def calculate_contribution_score(
    quality_score: float,
    impact_score: float,
    calibration_score: float,
) -> float:
    """Return final weighted contribution score."""
    return (
        0.5 * quality_score
        + 0.3 * impact_score
        + 0.2 * calibration_score
    )


def calculate_elo_delta(
    current_rating: float,
    council_average_rating: float,
    contribution_score: float,
) -> float:
    """Compute ELO change amount based on contribution and expectations."""
    expected = 1.0 / (
        1.0 + 10.0 ** ((council_average_rating - current_rating) / 400.0)
    )
    actual = contribution_score / 100.0
    delta = 10.0 * settings.reputation_k_factor * (actual - expected)
    return delta


def apply_reputation_update(current_rating: float, delta: float) -> float:
    """Apply delta to current rating, clamp to configuration limits, and round."""
    new_rating = current_rating + delta
    new_rating = max(
        settings.min_reputation,
        min(settings.max_reputation, new_rating)
    )
    return round(new_rating, 2)


def persist_reputation_history(
    session,
    expert_id: str,
    case_id: str,
    reputation_before: float,
    reputation_after: float,
    council_average_rating: float,
) -> ReputationHistory:
    """Create and return a ReputationHistory log entry in the session."""
    change_amount = round(reputation_after - reputation_before, 2)
    history = ReputationHistory(
        expert_id=expert_id,
        case_id=case_id,
        reputation_before=reputation_before,
        reputation_after=reputation_after,
        change_amount=change_amount,
        council_average_rating=council_average_rating,
    )
    session.add(history)
    return history


def get_val(obj, key, default=None):
    """Dynamically get an item/attribute from dict or Pydantic model."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


async def _process_in_session(
    session,
    case_id: str,
    analyses: list,
    rebuttals: list,
    expert_scores: list,
    strongest_argument: str,
    weakest_argument: str,
    consensus_verdict: str,
) -> list:
    logger.info(f"Processing reputation updates for case {case_id}...")

    updates_log = []

    expert_names = [
        get_val(s, "expert_name")
        for s in expert_scores
        if get_val(s, "expert_name")
    ]
    if not expert_names:
        logger.warning(f"No expert scores in judge rubric for case {case_id}. Skipping.")
        return []

    # Fetch participating experts from DB
    stmt = select(Expert).where(Expert.name.in_(expert_names))
    res = await session.execute(stmt)
    db_experts = {e.name.lower(): e for e in res.scalars().all()}

    valid_scores = []
    participating_db_experts = []

    for score in expert_scores:
        name = get_val(score, "expert_name")
        if not name:
            continue
        expert = db_experts.get(name.lower())
        if expert:
            participating_db_experts.append(expert)
            valid_scores.append((expert, score))
        else:
            logger.error(
                f"Expert '{name}' in judge rubric not found in database."
            )

    if not participating_db_experts:
        logger.warning("No valid database experts matched the judge rubric.")
        return

    # Council average rating
    R_avg = sum(e.reputation_score for e in participating_db_experts) / len(
        participating_db_experts
    )

    # Pass 1: Calculate raw contribution scores and ELO expectations
    expert_evaluations = []
    for expert, score in valid_scores:
        # Find matching analysis
        analysis = next(
            (
                a
                for a in analyses
                if get_val(a, "expert_name", "").lower() == expert.name.lower()
            ),
            None,
        )
        # Find matching rebuttal
        rebuttal = next(
            (
                r
                for r in rebuttals
                if get_val(r, "expert_name", "").lower() == expert.name.lower()
            ),
            None,
        )

        # 1. Quality Score
        judge_overall = get_val(score, "overall_score")
        if judge_overall is None:
            judge_overall = 0.0
        quality_score = calculate_quality_score(judge_overall)

        # 2. Impact Score
        impact_score = calculate_impact_score(
            expert_name=expert.name,
            strongest_argument=strongest_argument,
            weakest_argument=weakest_argument,
        )

        # 3. Calibration Score
        confidence = get_val(rebuttal, "updated_confidence")
        if confidence is None:
            confidence = get_val(analysis, "confidence")
        if confidence is None:
            confidence = 80.0

        calibration_score = calculate_calibration_score(
            confidence=confidence,
            quality_score=quality_score,
        )

        # 4. Contribution Score
        contribution_score = calculate_contribution_score(
            quality_score=quality_score,
            impact_score=impact_score,
            calibration_score=calibration_score,
        )

        R_old = expert.reputation_score
        expected = 1.0 / (
            1.0 + 10.0 ** ((R_avg - R_old) / 400.0)
        )

        expert_evaluations.append({
            "expert": expert,
            "analysis": analysis,
            "rebuttal": rebuttal,
            "confidence": confidence,
            "quality_score": quality_score,
            "impact_score": impact_score,
            "calibration_score": calibration_score,
            "contribution_score": contribution_score,
            "R_old": R_old,
            "expected": expected,
        })

    # Pass 2: Normalize actual scores and apply zero-sum ELO updates
    sum_contributions = sum(item["contribution_score"] for item in expert_evaluations)
    sum_expected = sum(item["expected"] for item in expert_evaluations)

    for item in expert_evaluations:
        expert = item["expert"]
        analysis = item["analysis"]
        confidence = item["confidence"]
        quality_score = item["quality_score"]
        impact_score = item["impact_score"]
        calibration_score = item["calibration_score"]
        contribution_score = item["contribution_score"]
        R_old = item["R_old"]
        expected = item["expected"]

        # Scale actual performance relative to the council average to enforce zero-sum
        if sum_contributions > 0:
            actual = (contribution_score / sum_contributions) * sum_expected
        else:
            actual = expected

        delta = 10.0 * settings.reputation_k_factor * (actual - expected)
        R_new = apply_reputation_update(current_rating=R_old, delta=delta)

        # Apply new score to expert
        expert.reputation_score = R_new

        # Extract analysis recommendations and reasoning
        recommendation = get_val(analysis, "recommendation", "approve")
        reasoning = get_val(analysis, "reasoning", "")

        recommendation_str = (
            recommendation.value
            if hasattr(recommendation, "value")
            else str(recommendation).lower()
        )

        self_critique = get_val(analysis, "self_critique", None)

        # Create ExpertParticipation
        participation = ExpertParticipation(
            expert_id=expert.id,
            case_id=case_id,
            role=ParticipationRole.COUNCIL_MEMBER,
            recommendation=recommendation_str,
            confidence=confidence,
            reasoning=reasoning,
            quality_score=round(quality_score, 2),
            impact_score=round(impact_score, 2),
            calibration_score=round(calibration_score, 2),
            contribution_score=round(contribution_score, 2),
            self_critique=self_critique,
        )
        session.add(participation)

        # Create ReputationHistory
        persist_reputation_history(
            session=session,
            expert_id=expert.id,
            case_id=case_id,
            reputation_before=R_old,
            reputation_after=R_new,
            council_average_rating=R_avg,
        )

        updates_log.append({
            "expert_name": expert.name,
            "reputation_before": R_old,
            "reputation_after": R_new,
            "change_amount": round(R_new - R_old, 2),
            "quality_score": round(quality_score, 2),
            "impact_score": round(impact_score, 2),
            "calibration_score": round(calibration_score, 2),
            "contribution_score": round(contribution_score, 2)
        })

        logger.info(
            f"Updated reputation for {expert.name}: "
            f"{R_old} -> {R_new} (delta={round(R_new - R_old, 2)}). "
            f"Contribution score: {round(contribution_score, 2)} "
            f"(Quality={round(quality_score, 2)}, Impact={round(impact_score, 2)}, Calib={round(calibration_score, 2)})"
        )
    return updates_log


async def process_reputation_updates(
    case_id: str,
    analyses: list,
    rebuttals: list,
    expert_scores: list,
    strongest_argument: str,
    weakest_argument: str,
    consensus_verdict: str,
    session=None,
) -> list:
    """
    Coordinates and persists the complete contribution scoring and ELO updates
    for all experts participating in a case inside a database transaction.
    """
    if session is not None:
        return await _process_in_session(
            session=session,
            case_id=case_id,
            analyses=analyses,
            rebuttals=rebuttals,
            expert_scores=expert_scores,
            strongest_argument=strongest_argument,
            weakest_argument=weakest_argument,
            consensus_verdict=consensus_verdict,
        )
    else:
        async with AsyncSessionLocal() as fresh_session:
            async with fresh_session.begin():
                return await _process_in_session(
                    session=fresh_session,
                    case_id=case_id,
                    analyses=analyses,
                    consensus_verdict=consensus_verdict,
                )


async def calculate_simulated_reputation_updates(
    analyses: list,
    rebuttals: list,
    expert_scores: list,
    strongest_argument: str,
    weakest_argument: str,
    case_id: str = None,
) -> list:
    """
    Computes simulated reputation updates and persists them to the database
    to support ELO state shifts and self-healing engine testing in demo mode.
    """
    expert_names = [
        get_val(s, "expert_name")
        for s in expert_scores
        if get_val(s, "expert_name")
    ]
    
    updates_log = []
    
    # 1. Fetch existing experts from the DB (if any match)
    db_experts = {}
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(Expert).where(Expert.name.in_(expert_names))
            res = await session.execute(stmt)
            db_experts = {e.name.lower(): e for e in res.scalars().all()}
    except Exception as exc:
        logger.warning(f"Failed to fetch expert ratings for simulation: {exc}")

    starting_ratings = []
    for score in expert_scores:
        name = get_val(score, "expert_name")
        if not name:
            continue
        expert = db_experts.get(name.lower())
        r_old = expert.reputation_score if expert else settings.starting_reputation
        starting_ratings.append(r_old)
        
    if not starting_ratings:
        return []
        
    R_avg = sum(starting_ratings) / len(starting_ratings)

    # Pass 1: Calculate raw contributions and expected scores
    expert_evaluations = []
    for score in expert_scores:
        name = get_val(score, "expert_name")
        if not name:
            continue
            
        expert = db_experts.get(name.lower())
        R_old = expert.reputation_score if expert else settings.starting_reputation
        
        # 1. Quality Score
        judge_overall = get_val(score, "overall_score")
        if judge_overall is None:
            judge_overall = 0.0
        quality_score = calculate_quality_score(judge_overall)
        
        # 2. Impact Score
        impact_score = calculate_impact_score(
            expert_name=name,
            strongest_argument=strongest_argument,
            weakest_argument=weakest_argument,
        )
        
        # 3. Calibration Score
        analysis = next(
            (a for a in analyses if get_val(a, "expert_name", "").lower() == name.lower()),
            None
        )
        rebuttal = next(
            (r for r in rebuttals if get_val(r, "expert_name", "").lower() == name.lower()),
            None
        )
        
        confidence = get_val(rebuttal, "updated_confidence")
        if confidence is None:
            confidence = get_val(analysis, "confidence")
        if confidence is None:
            confidence = 80.0
            
        calibration_score = calculate_calibration_score(
            confidence=confidence,
            quality_score=quality_score,
        )
        
        # 4. Contribution Score
        contribution_score = calculate_contribution_score(
            quality_score=quality_score,
            impact_score=impact_score,
            calibration_score=calibration_score,
        )

        expected = 1.0 / (
            1.0 + 10.0 ** ((R_avg - R_old) / 400.0)
        )

        expert_evaluations.append({
            "name": name,
            "expert": expert,
            "analysis": analysis,
            "quality_score": quality_score,
            "impact_score": impact_score,
            "calibration_score": calibration_score,
            "contribution_score": contribution_score,
            "R_old": R_old,
            "expected": expected,
            "confidence": confidence,
        })
        
    # Pass 2: Normalize, calculate ELO deltas, and write to database for existing experts
    sum_contributions = sum(item["contribution_score"] for item in expert_evaluations)
    sum_expected = sum(item["expected"] for item in expert_evaluations)

    db_experts_to_save = [item["expert"] for item in expert_evaluations if item["expert"] is not None]
    
    if db_experts_to_save or (case_id and db_experts):
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    for item in expert_evaluations:
                        name = item["name"]
                        expert = item["expert"]
                        analysis = item["analysis"]
                        quality_score = item["quality_score"]
                        impact_score = item["impact_score"]
                        calibration_score = item["calibration_score"]
                        contribution_score = item["contribution_score"]
                        R_old = item["R_old"]
                        expected = item["expected"]
                        confidence = item["confidence"]

                        if sum_contributions > 0:
                            actual = (contribution_score / sum_contributions) * sum_expected
                        else:
                            actual = expected

                        delta = 10.0 * settings.reputation_k_factor * (actual - expected)
                        R_new = apply_reputation_update(current_rating=R_old, delta=delta)
                        
                        if expert:
                            db_expert = await session.get(Expert, expert.id)
                            if db_expert:
                                db_expert.reputation_score = R_new
                                
                                if case_id:
                                    persist_reputation_history(
                                        session=session,
                                        expert_id=db_expert.id,
                                        case_id=case_id,
                                        reputation_before=R_old,
                                        reputation_after=R_new,
                                        council_average_rating=R_avg,
                                    )
                                    
                                    recommendation = get_val(analysis, "recommendation", "approve")
                                    reasoning = get_val(analysis, "reasoning", "")
                                    recommendation_str = (
                                        recommendation.value
                                        if hasattr(recommendation, "value")
                                        else str(recommendation).lower()
                                    )
                                    
                                    self_critique = get_val(analysis, "self_critique", None)
                                    
                                    # Dynamically generate simulated self-critique if expert is in recovery mode in demo runs
                                    from app.reflection.service import is_expert_in_recovery
                                    if await is_expert_in_recovery(session, db_expert.id) and not self_critique:
                                        self_critique = (
                                            f"[Simulated Self-Critique] Reviewing my previous failures, I acknowledge "
                                            f"my previous analysis in {db_expert.domain} lacked concrete metrics. "
                                            f"I will incorporate rigorous evidence in this evaluation."
                                        )

                                    participation = ExpertParticipation(
                                        expert_id=db_expert.id,
                                        case_id=case_id,
                                        role=ParticipationRole.COUNCIL_MEMBER,
                                        recommendation=recommendation_str,
                                        confidence=confidence,
                                        reasoning=reasoning,
                                        quality_score=round(quality_score, 2),
                                        impact_score=round(impact_score, 2),
                                        calibration_score=round(calibration_score, 2),
                                        contribution_score=round(contribution_score, 2),
                                        self_critique=self_critique,
                                    )
                                    session.add(participation)
                        
                        updates_log.append({
                            "expert_name": name,
                            "reputation_before": R_old,
                            "reputation_after": R_new,
                            "change_amount": round(R_new - R_old, 2),
                            "quality_score": round(quality_score, 2),
                            "impact_score": round(impact_score, 2),
                            "calibration_score": round(calibration_score, 2),
                            "contribution_score": round(contribution_score, 2)
                        })
                        logger.info(
                            f"Updated reputation (demo mode, DB persisted) for {name}: "
                            f"{R_old} -> {R_new} (delta={round(R_new - R_old, 2)})."
                        )
        except Exception as exc:
            logger.exception(f"Failed to persist simulated reputation updates to database: {exc}")
            updates_log = []
    
    if not updates_log:
        for item in expert_evaluations:
            name = item["name"]
            quality_score = item["quality_score"]
            impact_score = item["impact_score"]
            calibration_score = item["calibration_score"]
            contribution_score = item["contribution_score"]
            R_old = item["R_old"]
            expected = item["expected"]

            if sum_contributions > 0:
                actual = (contribution_score / sum_contributions) * sum_expected
            else:
                actual = expected

            delta = 10.0 * settings.reputation_k_factor * (actual - expected)
            R_new = apply_reputation_update(current_rating=R_old, delta=delta)
            
            updates_log.append({
                "expert_name": name,
                "reputation_before": R_old,
                "reputation_after": R_new,
                "change_amount": round(R_new - R_old, 2),
                "quality_score": round(quality_score, 2),
                "impact_score": round(impact_score, 2),
                "calibration_score": round(calibration_score, 2),
                "contribution_score": round(contribution_score, 2)
            })
            
    return updates_log

