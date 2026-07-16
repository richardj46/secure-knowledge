from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from sqlalchemy.orm import Session

from secure_knowledge_core.answers.context import ContextPassage
from secure_knowledge_core.answers.exceptions import (
    CitationValidationError,
    ConversationAccessDeniedError,
)
from secure_knowledge_core.answers.repository import AnswerRepository
from secure_knowledge_core.answers.retrieval_policy import (
    RetrievalSufficiencyPolicy,
)
from secure_knowledge_core.answers.schemas import (
    AnswerCitationRead,
    AnswerRequest,
    AnswerResponse,
    GeneratedAnswer,
)
from secure_knowledge_core.answers.validation import (
    validate_generated_answer,
)
from secure_knowledge_core.conversations.repository import (
    ConversationRepository,
)
from secure_knowledge_core.database.enums import (
    Answerability,
    AnswerGenerationStatus,
    MessageRole,
)
from secure_knowledge_core.database.models import (
    AnswerCitation,
    AnswerRun,
    Conversation,
    Message,
)
from secure_knowledge_core.llm.interface import AnswerProvider
from secure_knowledge_core.retrieval.authorization import RetrievalAuthorization
from secure_knowledge_core.retrieval.schemas import RetrievalSearchRequest
from secure_knowledge_core.retrieval.service import RetrievalService


class AnswerService:
    def __init__(
        self,
        *,
        session: Session,
        retrieval_service: RetrievalService,
        answer_provider: AnswerProvider,
        sufficiency_policy: RetrievalSufficiencyPolicy | None = None,
    ) -> None:
        self.session = session
        self.retrieval_service = retrieval_service
        self.answer_provider = answer_provider
        self.sufficiency_policy = (
            sufficiency_policy or RetrievalSufficiencyPolicy()
        )
        self.authorization = RetrievalAuthorization(session)
        self.conversations = ConversationRepository(session)
        self.answers = AnswerRepository(session)

    def answer(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        request: AnswerRequest,
    ) -> AnswerResponse:
        self.authorization.require_organization_membership(
            organization_id=organization_id,
            actor_user_id=user_id,
        )

        conversation = self._resolve_conversation(
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=request.conversation_id,
        )

        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.question,
        )

        self.session.add(user_message)
        self.session.flush()
        self.session.commit()

        retrieval = self.retrieval_service.search(
            organization_id=organization_id,
            user_id=user_id,
            request=RetrievalSearchRequest(
                query=request.question,
                workspace_ids=request.workspace_ids,
                limit=10,
            ),
        )
        self.session.commit()

        if not self.sufficiency_policy.is_sufficient(
            retrieval.results
        ):
            generated = GeneratedAnswer(
                answer=(
                    "I could not find enough authorized evidence "
                    "to answer this question."
                ),
                answerability=Answerability.NOT_FOUND,
                confidence=0.0,
                citations=[],
                limitations=[
                    "No sufficiently relevant authorized passages "
                    "were retrieved."
                ],
            )

            return self._persist_success(
                organization_id=organization_id,
                user_id=user_id,
                conversation=conversation,
                retrieval_run_id=retrieval.retrieval_run_id,
                generated=generated,
                passages=[],
                model_name=None,
                duration_ms=0,
            )

        passages = [
            ContextPassage(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                document_title=result.document_title,
                page_number=result.page_number,
                section_title=result.section_title,
                content=result.content,
            )
            for result in retrieval.results
        ]

        started_at = perf_counter()

        allowed_chunk_ids = {
            passage.chunk_id for passage in passages
        }

        try:
            generated = self.answer_provider.generate_answer(
                question=request.question,
                context=passages,
            )
            validate_generated_answer(
                generated=generated,
                allowed_chunk_ids=allowed_chunk_ids,
            )
        except Exception as exc:
            self.session.rollback()
            try:
                self._record_failed_run(
                    organization_id=organization_id,
                    user_id=user_id,
                    conversation_id=conversation.id,
                    retrieval_run_id=retrieval.retrieval_run_id,
                    failure=exc,
                )
            except Exception:
                self.session.rollback()
            raise

        duration_ms = int((perf_counter() - started_at) * 1000)

        return self._persist_success(
            organization_id=organization_id,
            user_id=user_id,
            conversation=conversation,
            retrieval_run_id=retrieval.retrieval_run_id,
            generated=generated,
            passages=passages,
            model_name=self._answer_provider_name(),
            duration_ms=duration_ms,
        )

    def _resolve_conversation(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        conversation_id: UUID | None,
    ) -> Conversation:
        if conversation_id is not None:
            conversation = self.conversations.get_for_user(
                conversation_id=conversation_id,
                organization_id=organization_id,
                user_id=user_id,
            )
            if conversation is None:
                raise ConversationAccessDeniedError
            return conversation

        conversation = Conversation(
            organization_id=organization_id,
            user_id=user_id,
            title=None,
        )
        self.conversations.add_conversation(conversation)
        self.session.flush()
        return conversation

    def _persist_success(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        conversation: Conversation,
        retrieval_run_id: UUID,
        generated: GeneratedAnswer,
        passages: list[ContextPassage],
        model_name: str | None,
        duration_ms: int,
    ) -> AnswerResponse:
        passage_by_chunk_id = {
            passage.chunk_id: passage for passage in passages
        }
        answer_run = AnswerRun(
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conversation.id,
            retrieval_run_id=retrieval_run_id,
            generation_status=AnswerGenerationStatus.COMPLETED,
            model_name=model_name or "abstention-policy",
            answerability=generated.answerability,
            confidence=generated.confidence,
            latency_ms=duration_ms,
            completed_at=datetime.now(UTC),
        )
        self.answers.add_run(answer_run)
        self.session.flush()

        assistant_message = Message(
            conversation_id=conversation.id,
            answer_run_id=answer_run.id,
            role=MessageRole.ASSISTANT,
            content=generated.answer,
        )
        self.session.add(assistant_message)
        self.session.flush()

        response_citations: list[AnswerCitationRead] = []
        for index, citation_draft in enumerate(
            generated.citations,
            start=1,
        ):
            passage = passage_by_chunk_id[citation_draft.chunk_id]
            citation = AnswerCitation(
                answer_run_id=answer_run.id,
                message_id=assistant_message.id,
                chunk_id=passage.chunk_id,
                document_id=passage.document_id,
                citation_index=index,
                claims=citation_draft.claims,
            )
            self.answers.add_citation(citation)
            response_citations.append(
                AnswerCitationRead(
                    chunk_id=passage.chunk_id,
                    document_id=passage.document_id,
                    document_title=passage.document_title,
                    page_number=passage.page_number,
                    claims=citation_draft.claims,
                )
            )

        self.session.commit()

        return AnswerResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            answer_run_id=answer_run.id,
            answer=generated.answer,
            answerability=generated.answerability,
            confidence=generated.confidence,
            citations=response_citations,
            limitations=generated.limitations,
        )

    def _record_failed_run(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        conversation_id: UUID,
        retrieval_run_id: UUID,
        failure: Exception,
    ) -> None:
        answer_run = AnswerRun(
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conversation_id,
            retrieval_run_id=retrieval_run_id,
            generation_status=AnswerGenerationStatus.FAILED,
            model_name=self._answer_provider_name(),
            error_code=self._safe_failure_code(failure),
            completed_at=datetime.now(UTC),
        )
        self.answers.add_run(answer_run)
        self.session.commit()

    def _answer_provider_name(self) -> str:
        model = getattr(self.answer_provider, "model", None)
        if isinstance(model, str) and model:
            return model
        return type(self.answer_provider).__name__

    @staticmethod
    def _safe_failure_code(failure: Exception) -> str:
        if isinstance(failure, CitationValidationError):
            return "citation_validation_failed"
        return "answer_generation_failed"
