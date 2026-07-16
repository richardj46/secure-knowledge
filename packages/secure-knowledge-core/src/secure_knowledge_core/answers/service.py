from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from sqlalchemy.orm import Session

from secure_knowledge_core.answers.context import ContextPassage
from secure_knowledge_core.answers.context_selection import ContextSelector
from secure_knowledge_core.answers.exceptions import (
    AnswerGenerationFailedError,
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
from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.database.enums import (
    Answerability,
    AnswerGenerationStatus,
    ExecutionMode,
    MessageRole,
)
from secure_knowledge_core.database.models import (
    AnswerCitation,
    AnswerRun,
    Conversation,
    Message,
    RetrievalRun,
)
from secure_knowledge_core.llm.exceptions import (
    LLMInvalidStructuredOutputError,
    LLMProviderConfigurationError,
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMRefusalError,
)
from secure_knowledge_core.llm.interface import AnswerProvider, ModelUsage
from secure_knowledge_core.llm.pricing import CostCalculator
from secure_knowledge_core.retrieval.authorization import RetrievalAuthorization
from secure_knowledge_core.retrieval.schemas import RetrievalSearchRequest
from secure_knowledge_core.retrieval.service import RetrievalService
from secure_knowledge_core.versioning import (
    ANSWER_PROMPT_VERSION,
    AUTHORIZATION_POLICY_VERSION,
    CHUNKING_VERSION,
    GROUNDEDNESS_GRADER_VERSION,
    RETRIEVAL_CONFIGURATION_VERSION,
)


class AnswerService:
    def __init__(
        self,
        *,
        session: Session,
        retrieval_service: RetrievalService,
        answer_provider: AnswerProvider,
        context_selector: ContextSelector,
        cost_calculator: CostCalculator,
        sufficiency_policy: RetrievalSufficiencyPolicy | None = None,
        execution_mode: ExecutionMode = ExecutionMode.PRODUCTION,
    ) -> None:
        self.session = session
        self.retrieval_service = retrieval_service
        self.answer_provider = answer_provider
        self.context_selector = context_selector
        self.cost_calculator = cost_calculator
        self.sufficiency_policy = (
            sufficiency_policy or RetrievalSufficiencyPolicy()
        )
        self.authorization = RetrievalAuthorization(session)
        self.conversations = ConversationRepository(session)
        self.answers = AnswerRepository(session)
        self.execution_mode = execution_mode
        self.retrieval_service.execution_mode = execution_mode

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
                provider_name=None,
                model_name=None,
                provider_request_id=None,
                usage=None,
                estimated_cost_microusd=None,
                duration_ms=0,
                execution_mode=self.execution_mode,
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
        selected_passages = self.context_selector.select(passages)

        started_at = perf_counter()

        try:
            provider_result = self.answer_provider.generate_answer(
                question=request.question,
                context=selected_passages,
            )
        except LLMProviderError as exc:
            duration_ms = int((perf_counter() - started_at) * 1000)
            self.session.rollback()
            try:
                self._record_failed_run(
                    organization_id=organization_id,
                    user_id=user_id,
                    conversation_id=conversation.id,
                    retrieval_run_id=retrieval.retrieval_run_id,
                    failure_code=self._map_provider_failure(exc),
                    generation_duration_ms=duration_ms,
                    execution_mode=self.execution_mode,
                )
            except Exception:
                self.session.rollback()
            raise AnswerGenerationFailedError from exc

        duration_ms = int((perf_counter() - started_at) * 1000)
        generated = provider_result.generated_answer
        allowed_chunk_ids = {
            passage.chunk_id for passage in selected_passages
        }
        try:
            validate_generated_answer(
                generated=generated,
                allowed_chunk_ids=allowed_chunk_ids,
            )
        except CitationValidationError:
            self.session.rollback()
            try:
                self._record_failed_run(
                    organization_id=organization_id,
                    user_id=user_id,
                    conversation_id=conversation.id,
                    retrieval_run_id=retrieval.retrieval_run_id,
                    failure_code="citation_validation_failed",
                    generation_duration_ms=duration_ms,
                    execution_mode=self.execution_mode,
                )
            except Exception:
                self.session.rollback()
            raise

        estimated_cost_microusd = None
        if provider_result.usage is not None:
            estimated_cost_microusd = self.cost_calculator.calculate_microusd(
                model=provider_result.model_name,
                usage=provider_result.usage,
            )

        return self._persist_success(
            organization_id=organization_id,
            user_id=user_id,
            conversation=conversation,
            retrieval_run_id=retrieval.retrieval_run_id,
            generated=generated,
            passages=selected_passages,
            provider_name=self._answer_provider_id(),
            model_name=provider_result.model_name,
            provider_request_id=provider_result.provider_request_id,
            usage=provider_result.usage,
            estimated_cost_microusd=estimated_cost_microusd,
            duration_ms=duration_ms,
            execution_mode=self.execution_mode,
        )

    def _resolve_conversation(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        conversation_id: UUID | None,
    ) -> Conversation:
        if conversation_id is not None:
            if self.execution_mode == ExecutionMode.PRODUCTION:
                conversation = self.conversations.get_for_user(
                    conversation_id=conversation_id,
                    organization_id=organization_id,
                    user_id=user_id,
                )
            else:
                conversation = self.conversations.get_internal_owned(
                    conversation_id=conversation_id,
                    organization_id=organization_id,
                    user_id=user_id,
                    execution_mode=self.execution_mode,
                )
            if conversation is None:
                raise ConversationAccessDeniedError
            return conversation

        conversation = Conversation(
            organization_id=organization_id,
            user_id=user_id,
            title=None,
            execution_mode=self.execution_mode,
            is_evaluation=self.execution_mode == ExecutionMode.EVALUATION,
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
        provider_name: str | None,
        model_name: str | None,
        provider_request_id: str | None,
        usage: ModelUsage | None,
        estimated_cost_microusd: int | None,
        duration_ms: int,
        execution_mode: ExecutionMode,
    ) -> AnswerResponse:
        passage_by_chunk_id = {
            passage.chunk_id: passage for passage in passages
        }
        resolved_model_name = model_name or "abstention-policy"
        answer_run = AnswerRun(
            execution_mode=execution_mode,
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conversation.id,
            retrieval_run_id=retrieval_run_id,
            provider=provider_name,
            provider_request_id=provider_request_id,
            status=AnswerGenerationStatus.COMPLETED,
            model_name=resolved_model_name,
            answer_prompt_version=ANSWER_PROMPT_VERSION,
            grader_prompt_version=GROUNDEDNESS_GRADER_VERSION,
            answer_model=resolved_model_name,
            embedding_model=self._embedding_model_for_run(retrieval_run_id),
            reranker_model=get_settings().reranker_model,
            chunking_version=CHUNKING_VERSION,
            retrieval_configuration_version=(
                RETRIEVAL_CONFIGURATION_VERSION
            ),
            authorization_policy_version=AUTHORIZATION_POLICY_VERSION,
            answerability=generated.answerability,
            confidence=generated.confidence,
            input_tokens=usage.input_tokens if usage is not None else None,
            output_tokens=(
                usage.output_tokens if usage is not None else None
            ),
            total_tokens=usage.total_tokens if usage is not None else None,
            estimated_cost_microusd=estimated_cost_microusd,
            generation_duration_ms=duration_ms,
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
        failure_code: str,
        generation_duration_ms: int,
        execution_mode: ExecutionMode,
    ) -> None:
        answer_run = AnswerRun(
            execution_mode=execution_mode,
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conversation_id,
            retrieval_run_id=retrieval_run_id,
            provider=self._answer_provider_id(),
            status=AnswerGenerationStatus.FAILED,
            model_name=self._answer_provider_name(),
            answer_prompt_version=ANSWER_PROMPT_VERSION,
            grader_prompt_version=GROUNDEDNESS_GRADER_VERSION,
            answer_model=self._answer_provider_name(),
            embedding_model=self._embedding_model_for_run(retrieval_run_id),
            reranker_model=get_settings().reranker_model,
            chunking_version=CHUNKING_VERSION,
            retrieval_configuration_version=(
                RETRIEVAL_CONFIGURATION_VERSION
            ),
            authorization_policy_version=AUTHORIZATION_POLICY_VERSION,
            failure_code=failure_code,
            generation_duration_ms=generation_duration_ms,
            completed_at=datetime.now(UTC),
        )
        self.answers.add_run(answer_run)
        self.session.commit()

    def _embedding_model_for_run(self, retrieval_run_id: UUID) -> str:
        retrieval_run = self.session.get(RetrievalRun, retrieval_run_id)
        if retrieval_run is None:
            raise ValueError("The retrieval run does not exist.")
        return retrieval_run.embedding_model

    def _answer_provider_name(self) -> str:
        model = getattr(self.answer_provider, "model", None)
        if isinstance(model, str) and model:
            return model
        return type(self.answer_provider).__name__

    def _answer_provider_id(self) -> str | None:
        provider = getattr(self.answer_provider, "provider", None)
        if isinstance(provider, str) and provider:
            return provider
        return None

    @staticmethod
    def _map_provider_failure(failure: LLMProviderError) -> str:
        if isinstance(failure, LLMProviderConfigurationError):
            return "provider_configuration_error"
        if isinstance(failure, LLMProviderTimeoutError):
            return "provider_timeout"
        if isinstance(failure, LLMProviderRateLimitError):
            return "provider_rate_limit"
        if isinstance(failure, LLMProviderUnavailableError):
            return "provider_unavailable"
        if isinstance(failure, LLMInvalidStructuredOutputError):
            return "invalid_structured_output"
        if isinstance(failure, LLMRefusalError):
            return "provider_refusal"
        return "provider_error"
