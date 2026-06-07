"""
app/api/v1/router.py
─────────────────────
V1 API router — aggregates all endpoint routers under /api/v1.
Add new routers here as phases progress.
"""
from fastapi import APIRouter

from app.api.v1 import health, decisions, analytics

api_router = APIRouter()

# ── Phase 0 ───────────────────────────────────────────────────────────────────
api_router.include_router(health.router)

# ── Phase 1 ───────────────────────────────────────────────────────────────────
api_router.include_router(decisions.router)

# ── Phase 6 ───────────────────────────────────────────────────────────────────
api_router.include_router(analytics.router)

