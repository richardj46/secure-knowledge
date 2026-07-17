from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from secure_knowledge_core.admin.pagination import (
    Page,
    decode_datetime_cursor,
    decode_integer_cursor,
    encode_datetime_cursor,
    encode_integer_cursor,
)
from secure_knowledge_core.audit.events import AuditEventType
from secure_knowledge_core.audit.service import AuditService
from secure_knowledge_core.authorization.service import AuthorizationService
from secure_knowledge_core.database.enums import (
    Answerability,
    AnswerGenerationStatus,
    MessageRole,
    ReviewStatus,
)
from secure_knowledge_core.database.models import (
    AnswerCitation,
    AnswerReview,
    AnswerRun,
    Document,
    DocumentChunk,
    DocumentVersion,
    Message,
    RetrievalResultRecord,
    RetrievalRun,
)


class AdminAnswerRunNotFoundError(Exception):
    """Raised when an admin-visible answer run cannot be found."""


class AnswerCitationInspection(BaseModel):
    citation_index: int
    claim_index: int
    claim: str | None
    chunk_id: UUID
    chunk_content: str
    document_id: UUID
    document_title: str
    page_number: int | None
    section_title: str | None
    document_version: int


class AnswerRunSummary(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID
    question: str
    answerability: Answerability | None
    confidence: float | None
    model: str
    status: AnswerGenerationStatus
    failure_code: str | None
    total_latency_ms: int
    created_at: datetime


class AnswerRunDetail(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    question: str
    answer: str | None
    answerability: Answerability | None
    confidence: float | None
    conversation_id: UUID
    retrieval_run_id: UUID
    model: str
    prompt_version: str
    provider_request_id: str | None
    selected_chunk_ids: list[UUID]
    citations: list[AnswerCitationInspection]
    limitations: list[str]
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_microusd: int | None
    retrieval_latency_ms: int
    generation_latency_ms: int | None
    total_latency_ms: int
    status: AnswerGenerationStatus
    failure_code: str | None
    created_at: datetime
    completed_at: datetime | None


class AnswerReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReviewStatus
    groundedness_score: float | None = Field(default=None, ge=0.0, le=1.0)
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    citation_score: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = Field(default=None, max_length=5000)


class AnswerReviewRead(BaseModel):
    id: UUID
    answer_run_id: UUID
    reviewer_user_id: UUID
    status: ReviewStatus
    groundedness_score: float | None
    relevance_score: float | None
    citation_score: float | None
    notes: str | None
    created_at: datetime


class AdminAnswerService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.authorization = AuthorizationService(session)
        self.audit = AuditService(session)

    def list_runs(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        limit: int,
        cursor: str | None,
    ) -> Page[AnswerRunSummary]:
        self._require_admin(organization_id, actor_user_id)
        statement = (
            select(AnswerRun, RetrievalRun)
            .join(RetrievalRun, RetrievalRun.id == AnswerRun.retrieval_run_id)
            .where(
                AnswerRun.organization_id == organization_id,
                RetrievalRun.organization_id == organization_id,
            )
        )
        if cursor is not None:
            cursor_time, cursor_id = decode_datetime_cursor(cursor)
            statement = statement.where(
                or_(
                    AnswerRun.created_at < cursor_time,
                    and_(
                        AnswerRun.created_at == cursor_time,
                        AnswerRun.id < cursor_id,
                    ),
                )
            )
        rows = self.session.execute(
            statement.order_by(
                AnswerRun.created_at.desc(),
                AnswerRun.id.desc(),
            ).limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [
            AnswerRunSummary(
                id=run.id,
                user_id=run.user_id,
                conversation_id=run.conversation_id,
                question=retrieval.query,
                answerability=run.answerability,
                confidence=run.confidence,
                model=run.model_name,
                status=run.status,
                failure_code=run.failure_code,
                total_latency_ms=(
                    retrieval.duration_ms
                    + (run.generation_duration_ms or 0)
                ),
                created_at=run.created_at,
            )
            for run, retrieval in rows
        ]
        next_cursor = (
            encode_datetime_cursor(rows[-1][0].created_at, rows[-1][0].id)
            if has_more and rows
            else None
        )
        return Page(items=items, next_cursor=next_cursor)

    def get_run(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        answer_run_id: UUID,
    ) -> AnswerRunDetail:
        self._require_admin(organization_id, actor_user_id)
        row = self.session.execute(
            select(AnswerRun, RetrievalRun)
            .join(RetrievalRun, RetrievalRun.id == AnswerRun.retrieval_run_id)
            .where(
                AnswerRun.id == answer_run_id,
                AnswerRun.organization_id == organization_id,
                RetrievalRun.organization_id == organization_id,
            )
        ).one_or_none()
        if row is None:
            raise AdminAnswerRunNotFoundError

        run, retrieval = row
        answer = self.session.scalar(
            select(Message.content).where(
                Message.answer_run_id == run.id,
                Message.role == MessageRole.ASSISTANT,
            )
        )
        selected_chunk_ids = list(
            self.session.scalars(
                select(RetrievalResultRecord.chunk_id)
                .where(
                    RetrievalResultRecord.retrieval_run_id
                    == run.retrieval_run_id,
                    RetrievalResultRecord.selected_for_context.is_(True),
                )
                .order_by(RetrievalResultRecord.final_rank)
            )
        )
        citations = self._list_citations(
            organization_id=organization_id,
            answer_run_id=run.id,
        )
        return AnswerRunDetail(
            id=run.id,
            organization_id=run.organization_id,
            user_id=run.user_id,
            question=retrieval.query,
            answer=answer,
            answerability=run.answerability,
            confidence=run.confidence,
            conversation_id=run.conversation_id,
            retrieval_run_id=run.retrieval_run_id,
            model=run.model_name,
            prompt_version=run.answer_prompt_version,
            provider_request_id=run.provider_request_id,
            selected_chunk_ids=selected_chunk_ids,
            citations=citations,
            limitations=list(run.limitations),
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
            estimated_cost_microusd=run.estimated_cost_microusd,
            retrieval_latency_ms=retrieval.duration_ms,
            generation_latency_ms=run.generation_duration_ms,
            total_latency_ms=(
                retrieval.duration_ms + (run.generation_duration_ms or 0)
            ),
            status=run.status,
            failure_code=run.failure_code,
            created_at=run.created_at,
            completed_at=run.completed_at,
        )

    def list_citations(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        answer_run_id: UUID,
        limit: int,
        cursor: str | None,
    ) -> Page[AnswerCitationInspection]:
        self._require_admin(organization_id, actor_user_id)
        self._require_run(organization_id, answer_run_id)
        inspections = self._list_citations(
            organization_id=organization_id,
            answer_run_id=answer_run_id,
        )
        if cursor is not None:
            cursor_position, cursor_id = decode_integer_cursor(cursor)
            inspections = [
                inspection
                for inspection in inspections
                if self._citation_position(inspection) > cursor_position
                or (
                    self._citation_position(inspection) == cursor_position
                    and inspection.chunk_id > cursor_id
                )
            ]
        page_items = inspections[: limit + 1]
        has_more = len(page_items) > limit
        page_items = page_items[:limit]
        next_cursor = (
            encode_integer_cursor(
                self._citation_position(page_items[-1]),
                page_items[-1].chunk_id,
            )
            if has_more and page_items
            else None
        )
        return Page(items=page_items, next_cursor=next_cursor)

    @staticmethod
    def _citation_position(citation: AnswerCitationInspection) -> int:
        return citation.citation_index * 1_000_000 + citation.claim_index

    def create_review(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        answer_run_id: UUID,
        data: AnswerReviewCreate,
        request_id: str | None,
    ) -> AnswerReviewRead:
        self._require_admin(organization_id, actor_user_id)
        self._require_run(organization_id, answer_run_id)
        review = AnswerReview(
            answer_run_id=answer_run_id,
            reviewer_user_id=actor_user_id,
            status=data.status,
            groundedness_score=data.groundedness_score,
            relevance_score=data.relevance_score,
            citation_score=data.citation_score,
            notes=data.notes,
        )
        self.session.add(review)
        self.session.flush()
        self.audit.record(
            organization_id=organization_id,
            event_type=AuditEventType.ADMIN_ANSWER_REVIEWED,
            resource_type="answer_run",
            resource_id=answer_run_id,
            actor_user_id=actor_user_id,
            outcome="succeeded",
            request_id=request_id,
            details={
                "answer_review_id": str(review.id),
                "review_status": review.status.value,
            },
        )
        return AnswerReviewRead(
            id=review.id,
            answer_run_id=review.answer_run_id,
            reviewer_user_id=review.reviewer_user_id,
            status=review.status,
            groundedness_score=review.groundedness_score,
            relevance_score=review.relevance_score,
            citation_score=review.citation_score,
            notes=review.notes,
            created_at=review.created_at,
        )

    def _list_citations(
        self,
        *,
        organization_id: UUID,
        answer_run_id: UUID,
    ) -> list[AnswerCitationInspection]:
        rows = self.session.execute(
            select(
                AnswerCitation,
                Document.title.label("document_title"),
                DocumentChunk.content.label("chunk_content"),
                DocumentChunk.page_number,
                DocumentChunk.section_title,
                DocumentVersion.version_number,
            )
            .join(Document, Document.id == AnswerCitation.document_id)
            .join(DocumentChunk, DocumentChunk.id == AnswerCitation.chunk_id)
            .join(
                DocumentVersion,
                DocumentVersion.id == DocumentChunk.document_version_id,
            )
            .where(
                AnswerCitation.answer_run_id == answer_run_id,
                Document.organization_id == organization_id,
                DocumentChunk.organization_id == organization_id,
            )
            .order_by(AnswerCitation.citation_index)
        ).all()
        inspections: list[AnswerCitationInspection] = []
        for row in rows:
            claims: list[str | None] = list(row.AnswerCitation.claims) or [None]
            inspections.extend(
                AnswerCitationInspection(
                    citation_index=row.AnswerCitation.citation_index,
                    claim_index=claim_index,
                    claim=claim,
                    chunk_id=row.AnswerCitation.chunk_id,
                    chunk_content=row.chunk_content,
                    document_id=row.AnswerCitation.document_id,
                    document_title=row.document_title,
                    page_number=row.page_number,
                    section_title=row.section_title,
                    document_version=row.version_number,
                )
                for claim_index, claim in enumerate(claims, start=1)
            )
        return inspections

    def _require_run(
        self,
        organization_id: UUID,
        answer_run_id: UUID,
    ) -> AnswerRun:
        run = self.session.scalar(
            select(AnswerRun).where(
                AnswerRun.id == answer_run_id,
                AnswerRun.organization_id == organization_id,
            )
        )
        if run is None:
            raise AdminAnswerRunNotFoundError
        return run

    def _require_admin(
        self,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        self.authorization.require_admin_access(
            organization_id=organization_id,
            user_id=actor_user_id,
        )
