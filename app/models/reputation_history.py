"""
app/models/reputation_history.py
──────────────────────────────────
ReputationHistory model — tracks the history of expert reputation score updates.
"""
from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin


class ReputationHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reputation_history"

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    expert_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Score details ─────────────────────────────────────────────────────────
    reputation_before: Mapped[float] = mapped_column(Float, nullable=False)
    reputation_after: Mapped[float] = mapped_column(Float, nullable=False)
    change_amount: Mapped[float] = mapped_column(Float, nullable=False)
    council_average_rating: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    expert: Mapped["Expert"] = relationship(  # noqa: F821
        "Expert",
        back_populates="reputation_history",
    )
    case: Mapped["Case"] = relationship(  # noqa: F821
        "Case",
    )

    def __repr__(self) -> str:
        return (
            f"<ReputationHistory expert_id={self.expert_id!r} "
            f"before={self.reputation_before!r} after={self.reputation_after!r} "
            f"change={self.change_amount!r} council_avg={self.council_average_rating!r}>"
        )
