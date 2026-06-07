"""
app/api/v1/analytics.py
────────────────────────
API endpoints for system analytics, ELO leaderboard, timeline, and expert details.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.analytics import schemas
from app.analytics import service as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/leaderboard", response_model=list[schemas.ExpertLeaderboardItem])
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    """
    Get a list of all experts sorted by ELO rating with additional case metrics.
    """
    try:
        return await analytics_service.get_leaderboard_stats(db)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve leaderboard: {exc}"
        )


@router.get("/memory-bank", response_model=schemas.MemoryBankResponse)
async def get_memory_bank(db: AsyncSession = Depends(get_db)):
    """
    Get all generated failure reflections and success patterns.
    """
    try:
        return await analytics_service.get_memory_bank_data(db)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve memory bank: {exc}"
        )


@router.get("/timeline", response_model=list[schemas.TimelineItem])
async def get_timeline(db: AsyncSession = Depends(get_db)):
    """
    Get the global timeline of recent reputation history logs.
    """
    try:
        return await analytics_service.get_global_timeline(db, limit=50)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve reputation timeline: {exc}"
        )


@router.get("/experts/{expert_id}", response_model=schemas.ExpertDetailResponse)
async def get_expert_detail(expert_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get detailed metrics, case participations, ELO timeline, and self-critiques for a single expert.
    """
    try:
        detail = await analytics_service.get_expert_detail_stats(db, expert_id)
        if not detail:
            raise HTTPException(
                status_code=404,
                detail=f"Expert with ID '{expert_id}' not found."
            )
        return detail
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve expert details: {exc}"
        )
