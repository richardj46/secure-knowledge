from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import EXECUTION_MODE_ENUM, ExecutionMode
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

    execution_mode: Mapped[ExecutionMode] = mapped_column(
        EXECUTION_MODE_ENUM,
        nullable=False,
        default=ExecutionMode.PRODUCTION,
        index=True,
    )

    is_evaluation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    evaluation_case_result_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("evaluation_case_results.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
