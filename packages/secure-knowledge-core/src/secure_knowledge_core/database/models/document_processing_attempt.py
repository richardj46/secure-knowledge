from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class DocumentProcessingAttempt(IdMixin, TimestampMixin, Base):
    __tablename__ = "document_processing_attempts"

    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "attempt_number",
            name="uq_document_processing_attempts_version_number",
        ),
    )

    document_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    worker_task_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    extraction_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    chunking_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    embedding_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    extracted_character_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    chunk_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    failure_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
