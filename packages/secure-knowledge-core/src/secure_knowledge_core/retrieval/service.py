from time import perf_counter
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from secure_knowledge_core.database.enums import ExecutionMode
from secure_knowledge_core.database.models import OrganizationMembership, Workspace
from secure_knowledge_core.ingestion.embeddings import EmbeddingProvider
from secure_knowledge_core.ingestion.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
)
from secure_knowledge_core.retrieval.authorization import RetrievalAuthorization
from secure_knowledge_core.retrieval.embeddings import QueryEmbeddingService
from secure_knowledge_core.retrieval.exceptions import (
    RetrievalUnavailableError,
    WorkspaceFilterNotFoundError,
)
from secure_knowledge_core.retrieval.fusion import (
    deduplicate_results,
    reciprocal_rank_fusion,
)
from secure_knowledge_core.retrieval.repository import RetrievalRepository
from secure_knowledge_core.retrieval.schemas import (
    RetrievalResult,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from secure_knowledge_core.retrieval.tracing import (
    DatabaseRetrievalTracer,
    RetrievalTrace,
    RetrievalTracer,
    RetrievalTraceResult,
)


class RetrievalService:
    def __init__(
        self,
        *,
        session: Session,
        embedding_provider: EmbeddingProvider,
        authorization: RetrievalAuthorization | None = None,
        repository: RetrievalRepository | None = None,
        tracer: RetrievalTracer | None = None,
        execution_mode: ExecutionMode = ExecutionMode.PRODUCTION,
    ) -> None:
        self.session = session
        self.embedding_provider = embedding_provider
        self.authorization = authorization or RetrievalAuthorization(session)
        self.query_embeddings = QueryEmbeddingService(embedding_provider)
        self.repository = repository or RetrievalRepository(session)
        self.tracer = tracer or DatabaseRetrievalTracer(session)
        self.execution_mode = execution_mode

    def search(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        request: RetrievalSearchRequest,
    ) -> RetrievalSearchResponse:
        started_at = perf_counter()
        self.authorization.require_organization_membership(
            organization_id=organization_id,
            actor_user_id=user_id,
        )
        self._validate_workspace_filters(
            organization_id=organization_id,
            user_id=user_id,
            workspace_ids=request.workspace_ids,
        )
        try:
            query_embedding = self.query_embeddings.create_query_embedding(
                request.query
            )
        except (EmbeddingConfigurationError, EmbeddingProviderError):
            raise RetrievalUnavailableError from None

        candidate_limit = max(request.limit * 4, 20)
        vector_results = self.repository.vector_search(
            user_id=user_id,
            organization_id=organization_id,
            query_embedding=query_embedding,
            workspace_ids=request.workspace_ids,
            limit=candidate_limit,
        )
        keyword_results = self.repository.keyword_search(
            user_id=user_id,
            organization_id=organization_id,
            query=request.query,
            workspace_ids=request.workspace_ids,
            limit=candidate_limit,
        )
        results = deduplicate_results(
            reciprocal_rank_fusion(
                vector_results=vector_results,
                keyword_results=keyword_results,
            )
        )[: request.limit]
        retrieval_results = [
            RetrievalResult(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                document_title=item.document_title,
                content=item.content,
                page_number=item.page_number,
                section_title=item.section_title,
                score=item.fused_score,
                vector_rank=item.vector_rank,
                keyword_rank=item.keyword_rank,
                vector_score=item.vector_score,
                keyword_score=item.keyword_score,
                retrieval_sources=[
                    source
                    for source, rank in (
                        ("vector", item.vector_rank),
                        ("keyword", item.keyword_rank),
                    )
                    if rank is not None
                ],
            )
            for item in results
        ]
        retrieval_run_id = self.tracer.record(
            RetrievalTrace(
                organization_id=organization_id,
                user_id=user_id,
                query=request.query,
                requested_limit=request.limit,
                vector_candidate_count=len(vector_results),
                keyword_candidate_count=len(keyword_results),
                embedding_model=self._embedding_model_name(),
                duration_ms=round((perf_counter() - started_at) * 1000),
                results=[
                    RetrievalTraceResult(
                        chunk_id=result.chunk_id,
                        document_id=result.document_id,
                        final_rank=rank,
                        fused_score=result.score,
                        vector_rank=result.vector_rank,
                        keyword_rank=result.keyword_rank,
                    )
                    for rank, result in enumerate(retrieval_results, start=1)
                ],
                execution_mode=self.execution_mode,
            )
        )
        return RetrievalSearchResponse(
            retrieval_run_id=retrieval_run_id,
            query=request.query,
            results=retrieval_results,
        )

    def _embedding_model_name(self) -> str:
        model = getattr(self.embedding_provider, "model", None)
        if isinstance(model, str) and model:
            return model
        return type(self.embedding_provider).__name__

    def _validate_workspace_filters(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        workspace_ids: list[UUID],
    ) -> None:
        requested_ids = set(workspace_ids)
        if not requested_ids:
            return

        valid_ids = set(
            self.session.scalars(
                select(Workspace.id)
                .join(
                    OrganizationMembership,
                    and_(
                        OrganizationMembership.organization_id
                        == Workspace.organization_id,
                        OrganizationMembership.user_id == user_id,
                    ),
                )
                .where(
                    Workspace.organization_id == organization_id,
                    Workspace.id.in_(requested_ids),
                )
            )
        )
        if valid_ids != requested_ids:
            raise WorkspaceFilterNotFoundError
