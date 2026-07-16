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
    Answerability,
    AnswerGenerationStatus,
)
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class AnswerRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "answer_runs"

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
