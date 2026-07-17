from uuid import UUID

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    PERMISSION_PATH_ENUM,
    PermissionPath,
)
from secure_knowledge_core.database.mixins import IdMixin
from secure_knowledge_core.versioning import AUTHORIZATION_POLICY_VERSION


class RetrievalResultRecord(IdMixin, Base):
    __tablename__ = "retrieval_results"

    __table_args__ = (
        UniqueConstraint(
            "retrieval_run_id",
            "final_rank",
            name="uq_retrieval_results_run_rank",
        ),
        UniqueConstraint(
            "retrieval_run_id",
            "chunk_id",
            name="uq_retrieval_results_run_chunk",
        ),
    )

    retrieval_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("retrieval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    final_rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    fused_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    vector_rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    keyword_rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    selected_for_context: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    permission_path: Mapped[PermissionPath | None] = mapped_column(
        PERMISSION_PATH_ENUM,
        nullable=True,
    )

    permission_source_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )

    authorization_policy_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=AUTHORIZATION_POLICY_VERSION,
    )
