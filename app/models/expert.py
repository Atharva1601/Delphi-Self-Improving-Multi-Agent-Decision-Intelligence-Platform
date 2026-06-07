"""
app/models/expert.py
────────────────────
Expert model — represents a permanent expert in the Delphi system.
Experts have domain specializations, a reputation score,
and accumulate reflections over time.
"""
from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.database.base import Base, TimestampMixin, UUIDMixin


class Expert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "experts"

    # ── Identity ──────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    domain: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Primary domain: finance, legal, security, etc.",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of this expert's role.",
    )

    # ── Reputation ────────────────────────────────────────────────────────────
    reputation_score: Mapped[float] = mapped_column(
        Float,
        default=lambda: settings.starting_reputation,
        nullable=False,
        comment="ELO-inspired reputation score. Starts at settings.starting_reputation.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # ── Relationships (populated in later phases) ─────────────────────────────
    participations: Mapped[list["ExpertParticipation"]] = relationship(  # noqa: F821
        "ExpertParticipation",
        back_populates="expert",
        lazy="selectin",
    )

    reputation_history: Mapped[list["ReputationHistory"]] = relationship(  # noqa: F821
        "ReputationHistory",
        back_populates="expert",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    reflections: Mapped[list["Reflection"]] = relationship(  # noqa: F821
        "Reflection",
        back_populates="expert",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    success_patterns: Mapped[list["SuccessPattern"]] = relationship(  # noqa: F821
        "SuccessPattern",
        back_populates="expert",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Expert id={self.id!r} name={self.name!r} domain={self.domain!r}>"
