import hashlib
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from secure_knowledge_core.database.models import RetrievalResultRecord, RetrievalRun


@dataclass(frozen=True)
class RetrievalTraceResult:
    chunk_id: UUID
    document_id: UUID
    final_rank: int
    fused_score: float
    vector_rank: int | None
    keyword_rank: int | None


@dataclass(frozen=True)
class RetrievalTrace:
    organization_id: UUID
    user_id: UUID
    query: str
    requested_limit: int
    vector_candidate_count: int
    keyword_candidate_count: int
    embedding_model: str
    duration_ms: int
    results: list[RetrievalTraceResult]


class RetrievalTracer(Protocol):
    def record(self, trace: RetrievalTrace) -> None:
        ...


class DatabaseRetrievalTracer:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, trace: RetrievalTrace) -> None:
        run = RetrievalRun(
            organization_id=trace.organization_id,
            user_id=trace.user_id,
            query=trace.query,
            query_hash=hashlib.sha256(trace.query.encode("utf-8")).hexdigest(),
            requested_limit=trace.requested_limit,
            vector_candidate_count=trace.vector_candidate_count,
            keyword_candidate_count=trace.keyword_candidate_count,
            final_result_count=len(trace.results),
            embedding_model=trace.embedding_model,
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
                )
                for result in trace.results
            ]
        )
        self.session.flush()
