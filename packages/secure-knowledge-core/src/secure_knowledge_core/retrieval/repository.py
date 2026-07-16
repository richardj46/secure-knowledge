from dataclasses import dataclass
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import and_, cast, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from secure_knowledge_core.database.enums import (
    DocumentStatus,
    DocumentVersionStatus,
)
from secure_knowledge_core.database.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
)
from secure_knowledge_core.retrieval.authorization import (
    build_authorized_document_condition,
)


@dataclass(frozen=True)
class RankedChunk:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    page_number: int | None
    section_title: str | None
    score: float
    rank: int


def build_retrievable_chunk_condition(
    *,
    user_id: UUID,
    organization_id: UUID,
) -> ColumnElement[bool]:
    return and_(
        build_authorized_document_condition(
            user_id=user_id,
            organization_id=organization_id,
        ),
        DocumentChunk.organization_id == organization_id,
        Document.status == DocumentStatus.READY,
        DocumentVersion.status == DocumentVersionStatus.READY,
        Document.current_version_number == DocumentVersion.version_number,
    )


class RetrievalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def vector_search(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        query_embedding: list[float],
        workspace_ids: list[UUID],
        limit: int,
    ) -> list[RankedChunk]:
        distance = cast(
            DocumentChunk.embedding,
            Vector(len(query_embedding)),
        ).cosine_distance(query_embedding)

        statement = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                Document.title,
                DocumentChunk.content,
                DocumentChunk.page_number,
                DocumentChunk.section_title,
                distance.label("distance"),
            )
            .join(
                Document,
                Document.id == DocumentChunk.document_id,
            )
            .join(
                DocumentVersion,
                DocumentVersion.id == DocumentChunk.document_version_id,
            )
            .where(
                build_retrievable_chunk_condition(
                    user_id=user_id,
                    organization_id=organization_id,
                ),
                DocumentChunk.embedding.is_not(None),
            )
        )

        if workspace_ids:
            statement = statement.where(Document.workspace_id.in_(workspace_ids))

        statement = statement.order_by(distance, DocumentChunk.id).limit(limit)
        rows = self.session.execute(statement).all()

        return [
            RankedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                document_title=row.title,
                content=row.content,
                page_number=row.page_number,
                section_title=row.section_title,
                score=max(0.0, 1.0 - float(row.distance)),
                rank=index,
            )
            for index, row in enumerate(rows, start=1)
        ]

    def keyword_search(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        query: str,
        workspace_ids: list[UUID],
        limit: int,
    ) -> list[RankedChunk]:
        search_query = func.websearch_to_tsquery(
            "english",
            query,
        )
        rank_expression = func.ts_rank_cd(
            DocumentChunk.search_vector,
            search_query,
        )

        statement = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                Document.title,
                DocumentChunk.content,
                DocumentChunk.page_number,
                DocumentChunk.section_title,
                rank_expression.label("search_rank"),
            )
            .join(
                Document,
                Document.id == DocumentChunk.document_id,
            )
            .join(
                DocumentVersion,
                DocumentVersion.id == DocumentChunk.document_version_id,
            )
            .where(
                build_retrievable_chunk_condition(
                    user_id=user_id,
                    organization_id=organization_id,
                ),
                DocumentChunk.search_vector.op("@@")(search_query),
            )
        )

        if workspace_ids:
            statement = statement.where(Document.workspace_id.in_(workspace_ids))

        statement = statement.order_by(
            rank_expression.desc(),
            DocumentChunk.id,
        ).limit(limit)
        rows = self.session.execute(statement).all()

        return [
            RankedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                document_title=row.title,
                content=row.content,
                page_number=row.page_number,
                section_title=row.section_title,
                score=float(row.search_rank),
                rank=index,
            )
            for index, row in enumerate(rows, start=1)
        ]
