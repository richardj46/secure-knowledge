from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    EVALUATION_REVIEW_STATUS_ENUM,
    ReviewStatus,
)
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class EvaluationCaseReview(IdMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_case_reviews"

    evaluation_case_result_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("evaluation_case_results.id", ondelete="CASCADE"),
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
        EVALUATION_REVIEW_STATUS_ENUM,
        nullable=False,
        default=ReviewStatus.PENDING,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
