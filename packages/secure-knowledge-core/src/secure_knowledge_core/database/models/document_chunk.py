from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Computed,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from secure_knowledge_core.database.models.document import Document
    from secure_knowledge_core.database.models.document_version import DocumentVersion


class SearchVectorComputed(Computed):
    """PostgreSQL search-vector expression with a SQLite test fallback."""


@compiles(SearchVectorComputed)
def _compile_search_vector(
    element: SearchVectorComputed,
    compiler: Any,
    **kwargs: Any,
) -> str:
    return compiler.visit_computed_column(element, **kwargs)


@compiles(SearchVectorComputed, "sqlite")
def _compile_sqlite_search_vector(
    element: SearchVectorComputed,
    compiler: Any,
    **kwargs: Any,
) -> str:
    return "GENERATED ALWAYS AS ('') STORED"


class DocumentChunk(IdMixin, TimestampMixin, Base):
    __tablename__ = "document_chunks"

    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "chunk_index",
            name="uq_document_chunks_version_index",
        ),
        Index(
            "ix_document_chunks_organization_document",
            "organization_id",
            "document_id",
        ),
        Index(
            "ix_document_chunks_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    search_vector: Mapped[str] = mapped_column(
        Text().with_variant(TSVECTOR(), "postgresql"),
        SearchVectorComputed(
            "to_tsvector('english', coalesce(content, ''))",
            persisted=True,
        ),
        nullable=False,
    )

    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    section_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        JSON().with_variant(Vector(1536), "postgresql"),
        nullable=True,
    )

    document: Mapped[Document] = relationship()
    document_version: Mapped[DocumentVersion] = relationship()
