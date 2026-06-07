"""
app/core/dependencies.py
────────────────────────
FastAPI dependency injection providers.
Import and use these with Depends() in route handlers.
"""
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session per request.
    The session is automatically committed on success
    and rolled back + closed on any exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias for cleaner route signatures
DBSession = AsyncSession
