from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    DocumentStatus,
    DocumentVisibility,
)
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from secure_knowledge_core.database.models.document_group_permission import (
        DocumentGroupPermission,
    )
    from secure_knowledge_core.database.models.document_user_permission import (
        DocumentUserPermission,
    )
    from secure_knowledge_core.database.models.document_version import DocumentVersion


class Document(IdMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "slug",
            name="uq_documents_workspace_slug",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    source_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    storage_key: Mapped[str | None] = mapped_column(
        String(1000),
        unique=True,
        nullable=True,
    )

    visibility: Mapped[DocumentVisibility] = mapped_column(
        Enum(
            DocumentVisibility,
            name="document_visibility",
            native_enum=True,
        ),
        nullable=False,
        default=DocumentVisibility.WORKSPACE,
    )

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            native_enum=True,
        ),
        nullable=False,
        default=DocumentStatus.PENDING,
    )

    current_version_number: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )

    versions: Mapped[list[DocumentVersion]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    user_permissions: Mapped[list[DocumentUserPermission]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    group_permissions: Mapped[list[DocumentGroupPermission]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
