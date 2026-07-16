from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    ANSWER_GENERATION_STATUS_ENUM,
    ANSWERABILITY_ENUM,
    EXECUTION_MODE_ENUM,
    Answerability,
    AnswerGenerationStatus,
    ExecutionMode,
)
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin
from secure_knowledge_core.versioning import (
    ANSWER_PROMPT_VERSION,
    AUTHORIZATION_POLICY_VERSION,
    CHUNKING_VERSION,
    GROUNDEDNESS_GRADER_VERSION,
    RETRIEVAL_CONFIGURATION_VERSION,
)


class AnswerRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "answer_runs"

    execution_mode: Mapped[ExecutionMode] = mapped_column(
        EXECUTION_MODE_ENUM,
        nullable=False,
        default=ExecutionMode.PRODUCTION,
        index=True,
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    retrieval_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("retrieval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    provider_request_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        index=True,
    )

    model_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
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

    answer_model: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
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

    answerability: Mapped[Answerability | None] = mapped_column(
        ANSWERABILITY_ENUM,
        nullable=True,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    input_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    output_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    estimated_cost_microusd: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    generation_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[AnswerGenerationStatus] = mapped_column(
        ANSWER_GENERATION_STATUS_ENUM,
        nullable=False,
        default=AnswerGenerationStatus.PENDING,
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
