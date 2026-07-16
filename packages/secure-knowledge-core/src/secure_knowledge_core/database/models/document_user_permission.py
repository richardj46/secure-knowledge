from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    DOCUMENT_PERMISSION_LEVEL_ENUM,
    DocumentPermissionLevel,
)
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from secure_knowledge_core.database.models.document import Document
    from secure_knowledge_core.database.models.user import User


class DocumentUserPermission(IdMixin, TimestampMixin, Base):
    __tablename__ = "document_user_permissions"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "user_id",
            name="uq_document_user_permissions_document_user",
        ),
    )

    document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    level: Mapped[DocumentPermissionLevel] = mapped_column(
        DOCUMENT_PERMISSION_LEVEL_ENUM,
        nullable=False,
        default=DocumentPermissionLevel.VIEWER,
    )

    document: Mapped[Document] = relationship(
        back_populates="user_permissions",
    )

    user: Mapped[User] = relationship()
