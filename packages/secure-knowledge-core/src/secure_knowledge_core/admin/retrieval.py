from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, and_, cast, exists, func, or_, select
from sqlalchemy.orm import Session

from secure_knowledge_core.admin.pagination import (
    Page,
    decode_datetime_cursor,
    decode_integer_cursor,
    encode_datetime_cursor,
    encode_integer_cursor,
)
from secure_knowledge_core.authorization.service import AuthorizationService
from secure_knowledge_core.database.enums import PermissionPath
from secure_knowledge_core.database.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    RetrievalResultRecord,
    RetrievalRun,
)


class AdminRetrievalRunNotFoundError(Exception):
    """Raised when an admin-visible retrieval run cannot be found."""


class RetrievalRunDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    user_id: UUID
    query: str
    workspace_ids: list[UUID]
    embedding_model: str
    retrieval_configuration_version: str
    authorization_policy_version: str
    vector_candidate_count: int
    keyword_candidate_count: int
    fused_result_count: int
    selected_result_count: int
    embedding_duration_ms: int | None
    vector_duration_ms: int | None
    keyword_duration_ms: int | None
    fusion_duration_ms: int | None
    total_duration_ms: int
    created_at: datetime


class RetrievalNeighborChunkRead(BaseModel):
    chunk_id: UUID
    chunk_index: int
    content: str
    page_number: int | None
    section_title: str | None


class RetrievalTraceResultRead(BaseModel):
    final_rank: int
    chunk_id: UUID
    chunk_index: int
    content: str
    document_id: UUID
    document_title: str
    document_filename: str
    document_mime_type: str
    workspace_id: UUID
    document_version_id: UUID
    document_version_number: int
    page_number: int | None
    section_title: str | None
    vector_rank: int | None
    keyword_rank: int | None
    fused_score: float
    retrieval_sources: list[str]
    selected_for_context: bool
    permission_path: PermissionPath | None
    permission_source_id: UUID | None
    authorization_policy_version: str
    neighboring_chunks: list[RetrievalNeighborChunkRead]


class AdminRetrievalService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.authorization = AuthorizationService(session)

    def list_runs(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        user_id: UUID | None,
        workspace_id: UUID | None,
        document_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        empty_results: bool | None,
        minimum_duration_ms: int | None,
        query: str | None,
        limit: int,
        cursor: str | None,
    ) -> Page[RetrievalRunDetail]:
        self._require_admin(organization_id, actor_user_id)
        statement = select(RetrievalRun).where(
            RetrievalRun.organization_id == organization_id
        )
        if user_id is not None:
            statement = statement.where(RetrievalRun.user_id == user_id)
        if workspace_id is not None:
            statement = statement.where(
                or_(
                    cast(RetrievalRun.workspace_ids, String).contains(
                        str(workspace_id),
                        autoescape=True,
                    ),
                    exists(
                        select(1)
                        .select_from(RetrievalResultRecord)
                        .join(
                            Document,
                            Document.id
                            == RetrievalResultRecord.document_id,
                        )
                        .where(
                            RetrievalResultRecord.retrieval_run_id
                            == RetrievalRun.id,
                            Document.workspace_id == workspace_id,
                        )
                    ),
                )
            )
        if document_id is not None:
            statement = statement.where(
                exists(
                    select(1).where(
                        RetrievalResultRecord.retrieval_run_id
                        == RetrievalRun.id,
                        RetrievalResultRecord.document_id == document_id,
                    )
                )
            )
        if date_from is not None:
            statement = statement.where(RetrievalRun.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(RetrievalRun.created_at <= date_to)
        if empty_results is not None:
            comparison = (
                RetrievalRun.final_result_count == 0
                if empty_results
                else RetrievalRun.final_result_count > 0
            )
            statement = statement.where(comparison)
        if minimum_duration_ms is not None:
            statement = statement.where(
                RetrievalRun.duration_ms >= minimum_duration_ms
            )
        if query is not None and query.strip():
            statement = statement.where(
                func.lower(RetrievalRun.query).contains(
                    query.strip().lower(),
                    autoescape=True,
                )
            )
        if cursor is not None:
            cursor_time, cursor_id = decode_datetime_cursor(cursor)
            statement = statement.where(
                or_(
                    RetrievalRun.created_at < cursor_time,
                    and_(
                        RetrievalRun.created_at == cursor_time,
                        RetrievalRun.id < cursor_id,
                    ),
                )
            )

        runs = self.session.scalars(
            statement.order_by(
                RetrievalRun.created_at.desc(),
                RetrievalRun.id.desc(),
            )
            .limit(limit + 1)
        ).all()
        has_more = len(runs) > limit
        runs = runs[:limit]
        next_cursor = (
            encode_datetime_cursor(runs[-1].created_at, runs[-1].id)
            if has_more and runs
            else None
        )
        return Page(
            items=[self._to_detail(run) for run in runs],
            next_cursor=next_cursor,
        )

    def get_run(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        run_id: UUID,
    ) -> RetrievalRunDetail:
        self._require_admin(organization_id, actor_user_id)
        run = self.session.scalar(
            select(RetrievalRun).where(
                RetrievalRun.id == run_id,
                RetrievalRun.organization_id == organization_id,
            )
        )
        if run is None:
            raise AdminRetrievalRunNotFoundError
        return self._to_detail(run)

    def list_results(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        run_id: UUID,
        limit: int,
        cursor: str | None,
    ) -> Page[RetrievalTraceResultRead]:
        self._require_admin(organization_id, actor_user_id)
        run_exists = self.session.scalar(
            select(RetrievalRun.id).where(
                RetrievalRun.id == run_id,
                RetrievalRun.organization_id == organization_id,
            )
        )
        if run_exists is None:
            raise AdminRetrievalRunNotFoundError

        statement = (
            select(
                RetrievalResultRecord,
                Document.title.label("document_title"),
                Document.source_filename.label("document_filename"),
                Document.mime_type.label("document_mime_type"),
                Document.workspace_id,
                DocumentChunk.document_version_id,
                DocumentChunk.chunk_index,
                DocumentChunk.content,
                DocumentChunk.page_number,
                DocumentChunk.section_title,
                DocumentVersion.version_number.label(
                    "document_version_number"
                ),
            )
            .join(Document, Document.id == RetrievalResultRecord.document_id)
            .join(
                DocumentChunk,
                DocumentChunk.id == RetrievalResultRecord.chunk_id,
            )
            .join(
                DocumentVersion,
                DocumentVersion.id == DocumentChunk.document_version_id,
            )
            .where(
                RetrievalResultRecord.retrieval_run_id == run_id,
                Document.organization_id == organization_id,
                DocumentChunk.organization_id == organization_id,
            )
        )
        if cursor is not None:
            cursor_rank, cursor_id = decode_integer_cursor(cursor)
            statement = statement.where(
                or_(
                    RetrievalResultRecord.final_rank > cursor_rank,
                    and_(
                        RetrievalResultRecord.final_rank == cursor_rank,
                        RetrievalResultRecord.id > cursor_id,
                    ),
                )
            )
        rows = self.session.execute(
            statement.order_by(
                RetrievalResultRecord.final_rank,
                RetrievalResultRecord.id,
            ).limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        neighbor_requests = [
            (
                row.RetrievalResultRecord.chunk_id,
                row.RetrievalResultRecord.document_id,
                row.document_version_id,
                row.chunk_index,
            )
            for row in rows
        ]
        neighbors_by_chunk_id = self._load_neighboring_chunks(
            organization_id=organization_id,
            requests=neighbor_requests,
        )
        items = [
            RetrievalTraceResultRead(
                final_rank=row.RetrievalResultRecord.final_rank,
                chunk_id=row.RetrievalResultRecord.chunk_id,
                chunk_index=row.chunk_index,
                content=row.content,
                document_id=row.RetrievalResultRecord.document_id,
                document_title=row.document_title,
                document_filename=row.document_filename,
                document_mime_type=row.document_mime_type,
                workspace_id=row.workspace_id,
                document_version_id=row.document_version_id,
                document_version_number=row.document_version_number,
                page_number=row.page_number,
                section_title=row.section_title,
                vector_rank=row.RetrievalResultRecord.vector_rank,
                keyword_rank=row.RetrievalResultRecord.keyword_rank,
                fused_score=row.RetrievalResultRecord.fused_score,
                retrieval_sources=self._retrieval_sources(
                    vector_rank=row.RetrievalResultRecord.vector_rank,
                    keyword_rank=row.RetrievalResultRecord.keyword_rank,
                ),
                selected_for_context=(
                    row.RetrievalResultRecord.selected_for_context
                ),
                permission_path=row.RetrievalResultRecord.permission_path,
                permission_source_id=(
                    row.RetrievalResultRecord.permission_source_id
                ),
                authorization_policy_version=(
                    row.RetrievalResultRecord.authorization_policy_version
                ),
                neighboring_chunks=neighbors_by_chunk_id.get(
                    row.RetrievalResultRecord.chunk_id,
                    [],
                ),
            )
            for row in rows
        ]
        next_cursor = (
            encode_integer_cursor(
                rows[-1].RetrievalResultRecord.final_rank,
                rows[-1].RetrievalResultRecord.id,
            )
            if has_more and rows
            else None
        )
        return Page(items=items, next_cursor=next_cursor)

    def _load_neighboring_chunks(
        self,
        *,
        organization_id: UUID,
        requests: list[tuple[UUID, UUID, UUID, int]],
    ) -> dict[UUID, list[RetrievalNeighborChunkRead]]:
        if not requests:
            return {}

        conditions = [
            and_(
                DocumentChunk.document_id == document_id,
                DocumentChunk.document_version_id == document_version_id,
                DocumentChunk.chunk_index.in_(
                    [chunk_index - 1, chunk_index + 1]
                ),
            )
            for _, document_id, document_version_id, chunk_index in requests
        ]
        rows = self.session.execute(
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.document_version_id,
                DocumentChunk.chunk_index,
                DocumentChunk.content,
                DocumentChunk.page_number,
                DocumentChunk.section_title,
            )
            .where(
                DocumentChunk.organization_id == organization_id,
                or_(*conditions),
            )
            .order_by(
                DocumentChunk.document_version_id,
                DocumentChunk.chunk_index,
            )
        ).all()

        neighbors_by_chunk_id: dict[
            UUID, list[RetrievalNeighborChunkRead]
        ] = {}
        for target_id, document_id, version_id, chunk_index in requests:
            neighbors_by_chunk_id[target_id] = [
                RetrievalNeighborChunkRead(
                    chunk_id=row.id,
                    chunk_index=row.chunk_index,
                    content=row.content,
                    page_number=row.page_number,
                    section_title=row.section_title,
                )
                for row in rows
                if row.document_id == document_id
                and row.document_version_id == version_id
                and row.chunk_index in {chunk_index - 1, chunk_index + 1}
            ]
        return neighbors_by_chunk_id

    @staticmethod
    def _retrieval_sources(
        *,
        vector_rank: int | None,
        keyword_rank: int | None,
    ) -> list[str]:
        sources: list[str] = []
        if vector_rank is not None:
            sources.append("vector")
        if keyword_rank is not None:
            sources.append("keyword")
        return sources

    def _require_admin(
        self,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        self.authorization.require_admin_access(
            organization_id=organization_id,
            user_id=actor_user_id,
        )

    @staticmethod
    def _to_detail(run: RetrievalRun) -> RetrievalRunDetail:
        return RetrievalRunDetail(
            id=run.id,
            organization_id=run.organization_id,
            user_id=run.user_id,
            query=run.query,
            workspace_ids=[UUID(value) for value in run.workspace_ids],
            embedding_model=run.embedding_model,
            retrieval_configuration_version=(
                run.retrieval_configuration_version
            ),
            authorization_policy_version=run.authorization_policy_version,
            vector_candidate_count=run.vector_candidate_count,
            keyword_candidate_count=run.keyword_candidate_count,
            fused_result_count=run.fused_result_count,
            selected_result_count=run.selected_result_count,
            embedding_duration_ms=run.embedding_duration_ms,
            vector_duration_ms=run.vector_duration_ms,
            keyword_duration_ms=run.keyword_duration_ms,
            fusion_duration_ms=run.fusion_duration_ms,
            total_duration_ms=run.duration_ms,
            created_at=run.created_at,
        )
