from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    DOCUMENT_VERSION_STATUS_ENUM,
    DocumentVersionStatus,
)
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from secure_knowledge_core.database.models.document import Document


class DocumentVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "document_versions"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_document_version",
        ),
    )

    document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version_number: Mapped[int] = mapped_column(
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(
        String(1000),
        unique=True,
        nullable=False,
    )

    checksum: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        nullable=False,
    )

    status: Mapped[DocumentVersionStatus] = mapped_column(
        DOCUMENT_VERSION_STATUS_ENUM,
        nullable=False,
        default=DocumentVersionStatus.PENDING,
    )

    processing_stage: Mapped[DocumentVersionStatus | None] = mapped_column(
        DOCUMENT_VERSION_STATUS_ENUM,
        nullable=True,
        default=DocumentVersionStatus.PENDING,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    page_count: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    extracted_character_count: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    chunk_count: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    document: Mapped[Document] = relationship(
        back_populates="versions",
    )
