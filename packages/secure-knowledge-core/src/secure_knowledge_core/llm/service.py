from dataclasses import dataclass
from uuid import UUID

from secure_knowledge_core.answers.context import build_context_passages
from secure_knowledge_core.answers.schemas import GeneratedAnswer
from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.database.enums import Answerability
from secure_knowledge_core.llm.abstention import AbstentionPolicy
from secure_knowledge_core.llm.interface import AnswerProvider, ModelUsage
from secure_knowledge_core.retrieval.schemas import RetrievalResult


@dataclass(frozen=True)
class AnswerGenerationResult:
    answer: GeneratedAnswer
    model_name: str
    provider_request_id: str | None
    usage: ModelUsage | None
    provider_called: bool
    allowed_chunk_ids: frozenset[UUID]


class AnswerGenerationService:
    def __init__(
        self,
        *,
        provider: AnswerProvider,
        abstention_policy: AbstentionPolicy | None = None,
    ) -> None:
        self.provider = provider
        if abstention_policy is None:
            settings = get_settings()
            abstention_policy = AbstentionPolicy(
                minimum_retrieval_score=settings.answer_minimum_retrieval_score,
                minimum_vector_similarity=settings.answer_minimum_vector_similarity,
                minimum_passage_characters=(
                    settings.answer_minimum_passage_characters
                ),
            )
        self.abstention_policy = abstention_policy

    def generate(
        self,
        *,
        question: str,
        retrieval_results: list[RetrievalResult],
    ) -> GeneratedAnswer:
        return self.generate_with_metadata(
            question=question,
            retrieval_results=retrieval_results,
        ).answer

    def generate_with_metadata(
        self,
        *,
        question: str,
        retrieval_results: list[RetrievalResult],
    ) -> AnswerGenerationResult:
        decision = self.abstention_policy.evaluate(retrieval_results)
        if decision.should_abstain:
            assert decision.reason is not None
            return AnswerGenerationResult(
                answer=GeneratedAnswer(
                    answer=(
                        "I couldn't find sufficient supporting information "
                        "to answer that question."
                    ),
                    answerability=Answerability.NOT_FOUND,
                    confidence=1.0,
                    citations=[],
                    limitations=[decision.reason],
                ),
                model_name="abstention-policy",
                provider_request_id=None,
                usage=None,
                provider_called=False,
                allowed_chunk_ids=frozenset(),
            )

        allowed_chunk_ids = frozenset(
            result.chunk_id for result in decision.passages
        )
        provider_result = self.provider.generate_answer(
            question=question,
            context=build_context_passages(decision.passages),
        )
        return AnswerGenerationResult(
            answer=provider_result.generated_answer,
            model_name=provider_result.model_name,
            provider_request_id=provider_result.provider_request_id,
            usage=provider_result.usage,
            provider_called=True,
            allowed_chunk_ids=allowed_chunk_ids,
        )
