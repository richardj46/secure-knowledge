from uuid import UUID

from sqlalchemy.orm import Session

from secure_knowledge_core.answers.schemas import (
    AnswerCitationResponse,
    CitationDraft,
)
from secure_knowledge_core.database.enums import (
    AnswerGenerationStatus,
    MessageRole,
)
from secure_knowledge_core.database.models import (
    AnswerCitation,
    AnswerRun,
    Message,
)
from secure_knowledge_core.llm.service import AnswerGenerationResult
from secure_knowledge_core.retrieval.schemas import RetrievalResult


class AnswerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_message(
        self,
        *,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        self.session.add(message)
        self.session.flush()
        return message

    def add_run(self, answer_run: AnswerRun) -> None:
        self.session.add(answer_run)

    def add_citation(self, citation: AnswerCitation) -> None:
        self.session.add(citation)

    def add_completed_run(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        retrieval_run_id: UUID,
        generation: AnswerGenerationResult,
        latency_ms: int,
    ) -> AnswerRun:
        answer_run = AnswerRun(
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conversation_id,
            retrieval_run_id=retrieval_run_id,
            model_name=generation.model_name,
            answerability=generation.answer.answerability,
            confidence=generation.answer.confidence,
            latency_ms=latency_ms,
            generation_status=AnswerGenerationStatus.COMPLETED,
        )
        self.session.add(answer_run)
        self.session.flush()
        return answer_run

    def add_citations(
        self,
        *,
        answer_run_id: UUID,
        results_by_chunk_id: dict[UUID, RetrievalResult],
        citations: list[CitationDraft],
    ) -> list[AnswerCitationResponse]:
        responses: list[AnswerCitationResponse] = []
        for index, citation in enumerate(citations, start=1):
            result = results_by_chunk_id[citation.chunk_id]
            self.session.add(
                AnswerCitation(
                    answer_run_id=answer_run_id,
                    chunk_id=citation.chunk_id,
                    document_id=result.document_id,
                    citation_index=index,
                )
            )
            responses.append(
                AnswerCitationResponse(
                    document_id=result.document_id,
                    document_title=result.document_title,
                    chunk_id=citation.chunk_id,
                    page_number=result.page_number,
                    claims=citation.claims,
                )
            )
        self.session.flush()
        return responses
