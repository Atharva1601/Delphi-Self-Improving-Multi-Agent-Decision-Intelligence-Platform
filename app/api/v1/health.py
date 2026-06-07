"""
app/api/v1/health.py
────────────────────
Health check endpoint.
Verifies FastAPI is running and the database is reachable.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Returns the operational status of the API and database.
    Used by Phase 0 exit criteria tests and future monitoring.
    """
    # Verify DB connectivity with a cheap query
    await db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
        "database": "connected",
    }
