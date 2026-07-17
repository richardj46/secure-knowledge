from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    EVALUATION_RUN_STATUS_ENUM,
    EvaluationRunStatus,
)
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin
from secure_knowledge_core.versioning import (
    ANSWER_PROMPT_VERSION,
    AUTHORIZATION_POLICY_VERSION,
    CHUNKING_VERSION,
    GROUNDEDNESS_GRADER_VERSION,
    RETRIEVAL_CONFIGURATION_VERSION,
)


class EvaluationRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_runs"

    dataset_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("evaluation_datasets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    started_by_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    baseline_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("evaluation_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[EvaluationRunStatus] = mapped_column(
        EVALUATION_RUN_STATUS_ENUM,
        nullable=False,
        default=EvaluationRunStatus.PENDING,
    )

    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
    )

    code_revision: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    answer_prompt_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=ANSWER_PROMPT_VERSION,
    )

    grader_prompt_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=GROUNDEDNESS_GRADER_VERSION,
    )

    answer_model: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    embedding_model: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    reranker_model: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    chunking_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=CHUNKING_VERSION,
    )

    retrieval_configuration_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=RETRIEVAL_CONFIGURATION_VERSION,
    )

    authorization_policy_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=AUTHORIZATION_POLICY_VERSION,
    )

    total_cases: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    completed_cases: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    passed_cases: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    failed_cases: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    hard_gates_passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    quality_gates_passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    regression_passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failure_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
