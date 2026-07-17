from uuid import UUID

from sqlalchemy import CheckConstraint, Float, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    ANSWER_REVIEW_STATUS_ENUM,
    ReviewStatus,
)
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class AnswerReview(IdMixin, TimestampMixin, Base):
    __tablename__ = "answer_reviews"

    __table_args__ = (
        CheckConstraint(
            "groundedness_score IS NULL "
            "OR groundedness_score BETWEEN 0.0 AND 1.0",
            name="ck_answer_reviews_groundedness_score_range",
        ),
        CheckConstraint(
            "relevance_score IS NULL OR relevance_score BETWEEN 0.0 AND 1.0",
            name="ck_answer_reviews_relevance_score_range",
        ),
        CheckConstraint(
            "citation_score IS NULL OR citation_score BETWEEN 0.0 AND 1.0",
            name="ck_answer_reviews_citation_score_range",
        ),
    )

    answer_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("answer_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reviewer_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[ReviewStatus] = mapped_column(
        ANSWER_REVIEW_STATUS_ENUM,
        nullable=False,
        default=ReviewStatus.PENDING,
        index=True,
    )

    groundedness_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    citation_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
