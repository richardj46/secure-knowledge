from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class Conversation(IdMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

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

    title: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )
