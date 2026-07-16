from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class Group(IdMixin, TimestampMixin, Base):
    __tablename__ = "groups"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "name",
            name="uq_groups_organization_name",
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

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    memberships: Mapped[list["GroupMembership"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )

    document_permissions: Mapped[list["DocumentGroupPermission"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )