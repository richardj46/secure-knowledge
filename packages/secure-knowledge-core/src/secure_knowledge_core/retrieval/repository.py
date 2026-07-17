from dataclasses import dataclass
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import and_, cast, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from secure_knowledge_core.core.tracing import start_span
from secure_knowledge_core.database.enums import (
    DocumentStatus,
    DocumentVersionStatus,
    PermissionPath,
)
from secure_knowledge_core.database.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
)
from secure_knowledge_core.retrieval.authorization import (
    build_authorized_document_condition,
    build_document_permission_path_expression,
    build_document_permission_source_id_expression,
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


@dataclass(frozen=True)
class PermissionDecision:
    path: PermissionPath
    source_id: UUID | None


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


def load_document_permission_decisions(
    *,
    session: Session,
    user_id: UUID,
    organization_id: UUID,
    document_ids: set[UUID],
) -> dict[UUID, PermissionDecision]:
    attributes = {"organization_id": organization_id}
    if len(document_ids) == 1:
        attributes["document_id"] = next(iter(document_ids))
    with start_span(
        "authorization.resolve_document_access",
        attributes,
    ):
        if not document_ids:
            return {}

        permission_path = build_document_permission_path_expression(
            user_id=user_id,
            organization_id=organization_id,
        )
        permission_source_id = build_document_permission_source_id_expression(
            user_id=user_id,
            organization_id=organization_id,
        )
        rows = session.execute(
            select(
                Document.id,
                permission_path.label("permission_path"),
                permission_source_id.label("permission_source_id"),
            ).where(
                Document.organization_id == organization_id,
                Document.id.in_(document_ids),
            )
        ).all()
    return {
        row.id: PermissionDecision(
            path=PermissionPath(row.permission_path),
            source_id=row.permission_source_id,
        )
        for row in rows
    }


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

    def permission_decisions(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        document_ids: set[UUID],
    ) -> dict[UUID, PermissionDecision]:
        return load_document_permission_decisions(
            session=self.session,
            user_id=user_id,
            organization_id=organization_id,
            document_ids=document_ids,
        )
