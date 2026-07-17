from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    EVALUATION_CASE_STATUS_ENUM,
    HUMAN_REVIEW_STATUS_ENUM,
    EvaluationCaseStatus,
    HumanReviewStatus,
)
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class EvaluationCaseResult(IdMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_case_results"

    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "evaluation_case_id",
            name="uq_evaluation_case_results_run_case",
        ),
    )

    evaluation_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    evaluation_case_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("evaluation_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    retrieval_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )

    answer_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )

    status: Mapped[EvaluationCaseStatus] = mapped_column(
        EVALUATION_CASE_STATUS_ENUM,
        nullable=False,
    )

    actual_answerability: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    actual_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    retrieved_document_ids: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
    )

    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
    )

    context_chunk_ids: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    estimated_cost_microusd: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    deterministic_passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    hard_gates_passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    hard_gate_violations: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
    )

    overall_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    human_review_status: Mapped[HumanReviewStatus] = mapped_column(
        HUMAN_REVIEW_STATUS_ENUM,
        nullable=False,
        default=HumanReviewStatus.PENDING,
        index=True,
    )

    human_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    human_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
