from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


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

    extraction_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
    )

    document: Mapped["Document"] = relationship(
        back_populates="versions",
    )