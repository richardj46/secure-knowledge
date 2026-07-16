from uuid import UUID

from sqlalchemy import ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin


class AnswerCitation(IdMixin, Base):
    __tablename__ = "answer_citations"

    __table_args__ = (
        UniqueConstraint(
            "answer_run_id",
            "citation_index",
            name="uq_answer_citations_run_index",
        ),
        UniqueConstraint(
            "answer_run_id",
            "chunk_id",
            name="uq_answer_citations_run_chunk",
        ),
    )

    answer_run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("answer_runs.id", ondelete="CASCADE"),
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

    citation_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
