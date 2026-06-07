"""
app/database/base.py
────────────────────
SQLAlchemy async declarative base and shared mixins.
All models import Base from here to ensure they are
registered in the same metadata object (required for Alembic).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Shared declarative base for all Delphi models."""
    pass


class TimestampMixin:
    """
    Adds created_at / updated_at columns to any model.
    Uses timezone-aware UTC datetimes stored as strings in SQLite
    (SQLite does not have a native timestamp-with-tz type).
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class UUIDMixin:
    """
    Adds a UUID primary key.
    Stored as a string for SQLite compatibility; use uuid4() on creation.
    """
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
