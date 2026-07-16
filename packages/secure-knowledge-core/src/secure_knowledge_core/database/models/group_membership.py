from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class GroupMembership(IdMixin, TimestampMixin, Base):
    __tablename__ = "group_memberships"

    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "user_id",
            name="uq_group_memberships_group_user",
        ),
    )

    group_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    group: Mapped["Group"] = relationship(
        back_populates="memberships",
    )

    user: Mapped["User"] = relationship()