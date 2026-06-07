"""
app/database/init_db.py
───────────────────────
Database initialization utilities.
Used during app startup and in tests to create/verify tables.
"""
from loguru import logger

from app.database.base import Base
from app.database.session import engine

# Import all models here so their metadata is registered before create_all()
from app.models import expert, case, participation  # noqa: F401


async def create_tables() -> None:
    """Create all tables defined in the metadata (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified / created.")


async def drop_tables() -> None:
    """Drop all tables — use only in testing or dev teardown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("All database tables dropped.")
