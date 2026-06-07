"""
tests/integration/test_migrations.py
──────────────────────────────────────
Verifies the database schema is correctly migrated and
all core tables exist with the expected columns.
"""
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


@pytest.mark.asyncio
async def test_experts_table_exists(db_session: AsyncSession) -> None:
    """experts table must be present after migration."""
    result = await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='experts'")
    )
    assert result.scalar() == "experts"


@pytest.mark.asyncio
async def test_cases_table_exists(db_session: AsyncSession) -> None:
    """cases table must be present after migration."""
    result = await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='cases'")
    )
    assert result.scalar() == "cases"


@pytest.mark.asyncio
async def test_expert_participations_table_exists(db_session: AsyncSession) -> None:
    """expert_participations table must be present after migration."""
    result = await db_session.execute(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='expert_participations'"
        )
    )
    assert result.scalar() == "expert_participations"


@pytest.mark.asyncio
async def test_can_insert_and_query_expert(db_session: AsyncSession) -> None:
    """Basic DB write/read round-trip on the experts table."""
    from app.models import Expert

    expert = Expert(
        name="Finance Expert",
        domain="finance",
        description="Analyses financial risks and market impacts.",
    )
    db_session.add(expert)
    await db_session.flush()

    assert expert.id is not None
    assert expert.reputation_score == settings.starting_reputation
    assert expert.is_active is True


@pytest.mark.asyncio
async def test_reputation_history_table_exists(db_session: AsyncSession) -> None:
    """reputation_history table must be present after migration."""
    result = await db_session.execute(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='reputation_history'"
        )
    )
    assert result.scalar() == "reputation_history"
