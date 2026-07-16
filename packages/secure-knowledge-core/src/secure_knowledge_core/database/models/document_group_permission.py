from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    DOCUMENT_PERMISSION_LEVEL_ENUM,
    DocumentPermissionLevel,
)
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class DocumentGroupPermission(IdMixin, TimestampMixin, Base):
    __tablename__ = "document_group_permissions"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "group_id",
            name="uq_document_group_permissions_document_group",
        ),
    )

    document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    group_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    level: Mapped[DocumentPermissionLevel] = mapped_column(
        DOCUMENT_PERMISSION_LEVEL_ENUM,
        nullable=False,
        default=DocumentPermissionLevel.VIEWER,
    )

    document: Mapped["Document"] = relationship(
        back_populates="group_permissions",
    )

    group: Mapped["Group"] = relationship(
        back_populates="document_permissions",
    )
