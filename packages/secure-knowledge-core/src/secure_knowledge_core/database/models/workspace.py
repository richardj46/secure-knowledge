from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from secure_knowledge_core.database.models.organization import Organization
    from secure_knowledge_core.database.models.workspace_membership import (
        WorkspaceMembership,
    )


class Workspace(IdMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "slug",
            name="uq_workspaces_organization_slug",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    organization: Mapped[Organization] = relationship(
        back_populates="workspaces",
    )

    memberships: Mapped[list[WorkspaceMembership]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
