"""
app/models/case.py
──────────────────
Case model — represents a single decision request submitted to Delphi.
Stores the original query, routing metadata, and final verdict.
"""
from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin
import enum


class CaseStatus(str, enum.Enum):
    PENDING = "pending"
    ROUTING = "routing"
    COUNCIL_FORMATION = "council_formation"
    DEBATE = "debate"
    JUDGING = "judging"
    CONSENSUS = "consensus"
    COMPLETED = "completed"
    FAILED = "failed"


class CaseVerdict(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    CONDITIONAL_APPROVE = "conditional_approve"
    INCONCLUSIVE = "inconclusive"


class Case(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cases"

    # ── Input ─────────────────────────────────────────────────────────────────
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Original user query submitted to Delphi.",
    )

    # ── Routing metadata ──────────────────────────────────────────────────────
    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Industry detected by the router.",
    )
    domains: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-serialised list of relevant domains.",
    )

    # ── Workflow state ────────────────────────────────────────────────────────
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus),
        default=CaseStatus.PENDING,
        nullable=False,
    )

    # ── Output ────────────────────────────────────────────────────────────────
    verdict: Mapped[CaseVerdict | None] = mapped_column(
        Enum(CaseVerdict),
        nullable=True,
        comment="Final decision produced by the consensus engine.",
    )
    confidence: Mapped[float | None] = mapped_column(
        nullable=True,
        comment="Aggregate confidence score 0–100.",
    )
    executive_report: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Final report shown to the user.",
    )
    council_members: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-serialised list of selected expert names.",
    )
    raw_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full JSON debate result including all rounds, judge scores, consensus.",
    )
    stage_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Incremental JSON snapshots written after each pipeline stage for live UI polling.",
    )
    error_detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if status=FAILED.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    participations: Mapped[list["ExpertParticipation"]] = relationship(  # noqa: F821
        "ExpertParticipation",
        back_populates="case",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Case id={self.id!r} status={self.status!r} verdict={self.verdict!r}>"
        )
