"""
app/database/session.py
───────────────────────
Async SQLAlchemy engine and session factory.
Engine is configured to be database-agnostic:
swap DATABASE_URL to switch from SQLite → PostgreSQL with no code changes.
"""
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# connect_args is only needed for SQLite (enables WAL mode for concurrency).
_connect_args: dict = (
    {"check_same_thread": False}
    if "sqlite" in settings.database_url
    else {}
)

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,           # Log SQL statements in debug mode
    future=True,
    connect_args=_connect_args,
)

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,        # Keep objects usable after commit
    autocommit=False,
    autoflush=False,
)
