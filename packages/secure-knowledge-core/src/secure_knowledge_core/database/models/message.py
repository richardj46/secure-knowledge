from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import MESSAGE_ROLE_ENUM, MessageRole
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class Message(IdMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    answer_run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("answer_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    role: Mapped[MessageRole] = mapped_column(
        MESSAGE_ROLE_ENUM,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
