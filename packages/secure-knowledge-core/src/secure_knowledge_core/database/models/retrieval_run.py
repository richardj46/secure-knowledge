from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import EXECUTION_MODE_ENUM, ExecutionMode
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin


class RetrievalRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "retrieval_runs"

    execution_mode: Mapped[ExecutionMode] = mapped_column(
        EXECUTION_MODE_ENUM,
        nullable=False,
        default=ExecutionMode.PRODUCTION,
        index=True,
    )

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

    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    query_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    requested_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    vector_candidate_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    keyword_candidate_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    final_result_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    embedding_model: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    duration_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
