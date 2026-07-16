from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from secure_knowledge_core.answers.exceptions import (
    ConversationNotFoundError,
    RetrievalTraceMissingError,
)
from secure_knowledge_core.answers.schemas import (
    AnswerCitationResponse,
    AnswerResponse,
)
from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.database.enums import (
    AnswerGenerationStatus,
    MessageRole,
)
from secure_knowledge_core.database.models import (
    AnswerCitation,
    AnswerRun,
    Conversation,
    Message,
)
from secure_knowledge_core.llm.citations import validate_citations
from secure_knowledge_core.llm.schemas import CitationDraft
from secure_knowledge_core.llm.service import AnswerGenerationService
from secure_knowledge_core.retrieval.authorization import RetrievalAuthorization
from secure_knowledge_core.retrieval.schemas import (
    RetrievalResult,
    RetrievalSearchRequest,
)
from secure_knowledge_core.retrieval.service import RetrievalService


class AnswerService:
    def __init__(
        self,
        session: Session,
        *,
        authorization: RetrievalAuthorization | None = None,
        retrieval: RetrievalService | None = None,
        generation: AnswerGenerationService | None = None,
        retrieval_limit: int | None = None,
    ) -> None:
        self.session = session
        self.authorization = authorization or RetrievalAuthorization(session)
        self.retrieval = retrieval or RetrievalService(session)
        self.generation = generation or AnswerGenerationService()
        self.retrieval_limit = (
            retrieval_limit
            if retrieval_limit is not None
            else get_settings().answer_retrieval_limit
        )

    def answer(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        conversation_id: UUID | None,
        question: str,
        workspace_ids: list[UUID] | None = None,
    ) -> AnswerResponse:
        self.authorization.require_organization_membership(
            organization_id=organization_id,
            actor_user_id=user_id,
        )
        retrieval_request = RetrievalSearchRequest(
            query=question,
            workspace_ids=workspace_ids or [],
            limit=self.retrieval_limit,
        )
        conversation = self._get_or_create_conversation(
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conversation_id,
            question=question,
        )
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=question,
        )
        self.session.add(user_message)
        self.session.flush()

        retrieval_response = self.retrieval.search(
            organization_id=organization_id,
            user_id=user_id,
            request=retrieval_request,
        )
        retrieval_run_id = retrieval_response.retrieval_run_id
        if retrieval_run_id is None:
            raise RetrievalTraceMissingError

        generation_started_at = perf_counter()
        generation_result = self.generation.generate_with_metadata(
            question=question,
            retrieval_results=retrieval_response.results,
        )
        answer = generation_result.answer
        validate_citations(
            answer=answer,
            allowed_chunk_ids=set(generation_result.allowed_chunk_ids),
        )

        answer_run = AnswerRun(
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conversation.id,
            retrieval_run_id=retrieval_run_id,
            model_name=generation_result.model_name,
            answerability=answer.answerability,
            confidence=answer.confidence,
            latency_ms=round((perf_counter() - generation_started_at) * 1000),
            generation_status=AnswerGenerationStatus.COMPLETED,
        )
        self.session.add(answer_run)
        self.session.flush()

        results_by_chunk_id = {
            result.chunk_id: result for result in retrieval_response.results
        }
        citation_responses = self._store_citations(
            answer_run=answer_run,
            results_by_chunk_id=results_by_chunk_id,
            citations=answer.citations,
        )
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=answer.answer,
        )
        self.session.add(assistant_message)
        self.session.flush()

        return AnswerResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            answer=answer.answer,
            answerability=answer.answerability,
            confidence=answer.confidence,
            citations=citation_responses,
            limitations=answer.limitations,
        )

    def _get_or_create_conversation(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        conversation_id: UUID | None,
        question: str,
    ) -> Conversation:
        if conversation_id is None:
            conversation = Conversation(
                organization_id=organization_id,
                user_id=user_id,
                title=question.strip()[:300],
            )
            self.session.add(conversation)
            self.session.flush()
            return conversation

        conversation = self.session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.organization_id == organization_id,
                Conversation.user_id == user_id,
            )
        )
        if conversation is None:
            raise ConversationNotFoundError
        return conversation

    def _store_citations(
        self,
        *,
        answer_run: AnswerRun,
        results_by_chunk_id: dict[UUID, RetrievalResult],
        citations: list[CitationDraft],
    ) -> list[AnswerCitationResponse]:
        responses: list[AnswerCitationResponse] = []
        for index, citation in enumerate(citations, start=1):
            result = results_by_chunk_id[citation.chunk_id]
            self.session.add(
                AnswerCitation(
                    answer_run_id=answer_run.id,
                    chunk_id=citation.chunk_id,
                    document_id=result.document_id,
                    citation_index=index,
                )
            )
            responses.append(
                AnswerCitationResponse(
                    chunk_id=citation.chunk_id,
                    document_id=result.document_id,
                    document_title=result.document_title,
                    page_number=result.page_number,
                )
            )
        self.session.flush()
        return responses
