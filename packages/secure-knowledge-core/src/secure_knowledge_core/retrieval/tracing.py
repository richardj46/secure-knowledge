import hashlib
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from secure_knowledge_core.database.enums import ExecutionMode, PermissionPath
from secure_knowledge_core.database.models import (
    RetrievalResultRecord,
    RetrievalRun,
)
from secure_knowledge_core.versioning import AUTHORIZATION_POLICY_VERSION


@dataclass(frozen=True)
class RetrievalTraceResult:
    chunk_id: UUID
    document_id: UUID
    final_rank: int
    fused_score: float
    vector_rank: int | None
    keyword_rank: int | None
    permission_path: PermissionPath | None
    permission_source_id: UUID | None


@dataclass(frozen=True)
class RetrievalTrace:
    organization_id: UUID
    user_id: UUID
    query: str
    requested_limit: int
    vector_candidate_count: int
    keyword_candidate_count: int
    fused_result_count: int
    embedding_model: str
    duration_ms: int
    results: list[RetrievalTraceResult]
    workspace_ids: list[UUID]
    embedding_duration_ms: int | None = None
    vector_duration_ms: int | None = None
    keyword_duration_ms: int | None = None
    fusion_duration_ms: int | None = None
    authorization_policy_version: str = AUTHORIZATION_POLICY_VERSION
    execution_mode: ExecutionMode = ExecutionMode.PRODUCTION


class RetrievalTracer(Protocol):
    def record(self, trace: RetrievalTrace) -> UUID:
        ...


class DatabaseRetrievalTracer:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, trace: RetrievalTrace) -> UUID:
        run = RetrievalRun(
            execution_mode=trace.execution_mode,
            organization_id=trace.organization_id,
            user_id=trace.user_id,
            query=trace.query,
            query_hash=hashlib.sha256(trace.query.encode("utf-8")).hexdigest(),
            requested_limit=trace.requested_limit,
            workspace_ids=[
                str(workspace_id) for workspace_id in trace.workspace_ids
            ],
            vector_candidate_count=trace.vector_candidate_count,
            keyword_candidate_count=trace.keyword_candidate_count,
            fused_result_count=trace.fused_result_count,
            selected_result_count=0,
            final_result_count=len(trace.results),
            embedding_model=trace.embedding_model,
            authorization_policy_version=trace.authorization_policy_version,
            embedding_duration_ms=trace.embedding_duration_ms,
            vector_duration_ms=trace.vector_duration_ms,
            keyword_duration_ms=trace.keyword_duration_ms,
            fusion_duration_ms=trace.fusion_duration_ms,
            duration_ms=trace.duration_ms,
        )
        self.session.add(run)
        self.session.flush()

        self.session.add_all(
            [
                RetrievalResultRecord(
                    retrieval_run_id=run.id,
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    final_rank=result.final_rank,
                    fused_score=result.fused_score,
                    vector_rank=result.vector_rank,
                    keyword_rank=result.keyword_rank,
                    permission_path=result.permission_path,
                    permission_source_id=result.permission_source_id,
                    authorization_policy_version=(
                        trace.authorization_policy_version
                    ),
                )
                for result in trace.results
            ]
        )
        self.session.flush()
        return run.id


def mark_selected_context(
    *,
    session: Session,
    retrieval_run_id: UUID,
    chunk_ids: set[UUID],
) -> None:
    session.execute(
        update(RetrievalResultRecord)
        .where(RetrievalResultRecord.retrieval_run_id == retrieval_run_id)
        .values(selected_for_context=False)
    )
    if chunk_ids:
        session.execute(
            update(RetrievalResultRecord)
            .where(
                RetrievalResultRecord.retrieval_run_id == retrieval_run_id,
                RetrievalResultRecord.chunk_id.in_(chunk_ids),
            )
            .values(selected_for_context=True)
        )
    session.execute(
        update(RetrievalRun)
        .where(RetrievalRun.id == retrieval_run_id)
        .values(selected_result_count=len(chunk_ids))
    )
