from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import EXECUTION_MODE_ENUM, ExecutionMode
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin
from secure_knowledge_core.versioning import (
    AUTHORIZATION_POLICY_VERSION,
    RETRIEVAL_CONFIGURATION_VERSION,
)


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

    workspace_ids: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
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

    fused_result_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    selected_result_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    embedding_model: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    retrieval_configuration_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=RETRIEVAL_CONFIGURATION_VERSION,
    )

    authorization_policy_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=AUTHORIZATION_POLICY_VERSION,
    )

    embedding_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    vector_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    keyword_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    fusion_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    duration_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
