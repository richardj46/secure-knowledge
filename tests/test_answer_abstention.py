from uuid import uuid4

from secure_knowledge_core.database.enums import Answerability
from secure_knowledge_core.llm.abstention import AbstentionPolicy
from secure_knowledge_core.llm.context import ContextPassage
from secure_knowledge_core.llm.interface import (
    AnswerProviderResult,
    ModelUsage,
)
from secure_knowledge_core.llm.schemas import CitationDraft, GeneratedAnswer
from secure_knowledge_core.llm.service import AnswerGenerationService
from secure_knowledge_core.retrieval.schemas import RetrievalResult


class RecordingAnswerProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate_answer(
        self,
        *,
        question: str,
        context: list[ContextPassage],
    ) -> AnswerProviderResult:
        del question
        self.calls += 1
        return AnswerProviderResult(
            generated_answer=GeneratedAnswer(
                answer="Supported answer.",
                answerability=Answerability.ANSWERABLE,
                confidence=0.8,
                citations=[
                    CitationDraft(
                        chunk_id=context[0].chunk_id,
                        claims=["Supported answer."],
                    )
                ],
            ),
            model_name="recording-answer-model",
            provider_request_id="recording-request-id",
            usage=ModelUsage(
                input_tokens=10,
                output_tokens=4,
                total_tokens=14,
            ),
        )


def policy() -> AbstentionPolicy:
    return AbstentionPolicy(
        minimum_retrieval_score=0.015,
        minimum_vector_similarity=0.55,
        minimum_passage_characters=40,
    )


def result(
    *,
    score: float = 0.02,
    vector_score: float | None = 0.8,
    keyword_rank: int | None = None,
    content: str = "A sufficiently detailed passage that supports the requested answer.",
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Guide",
        content=content,
        page_number=1,
        section_title=None,
        score=score,
        vector_rank=1,
        keyword_rank=keyword_rank,
        vector_score=vector_score,
        retrieval_sources=["vector"],
    )


def test_empty_retrieval_abstains_without_calling_provider() -> None:
    provider = RecordingAnswerProvider()
    service = AnswerGenerationService(
        provider=provider,
        abstention_policy=policy(),
    )

    answer = service.generate(question="Question?", retrieval_results=[])

    assert answer.answerability is Answerability.NOT_FOUND
    assert answer.citations == []
    assert provider.calls == 0


def test_low_retrieval_scores_abstain() -> None:
    provider = RecordingAnswerProvider()
    service = AnswerGenerationService(
        provider=provider,
        abstention_policy=policy(),
    )

    answer = service.generate(
        question="Question?",
        retrieval_results=[result(score=0.01)],
    )

    assert answer.answerability is Answerability.NOT_FOUND
    assert provider.calls == 0


def test_unrelated_vector_results_abstain() -> None:
    provider = RecordingAnswerProvider()
    service = AnswerGenerationService(
        provider=provider,
        abstention_policy=policy(),
    )

    answer = service.generate(
        question="Question?",
        retrieval_results=[result(vector_score=0.2)],
    )

    assert answer.answerability is Answerability.NOT_FOUND
    assert provider.calls == 0


def test_passages_without_enough_text_abstain() -> None:
    provider = RecordingAnswerProvider()
    service = AnswerGenerationService(
        provider=provider,
        abstention_policy=policy(),
    )

    answer = service.generate(
        question="Question?",
        retrieval_results=[result(content="Too short.")],
    )

    assert answer.answerability is Answerability.NOT_FOUND
    assert provider.calls == 0


def test_supported_results_are_sent_to_provider() -> None:
    provider = RecordingAnswerProvider()
    service = AnswerGenerationService(
        provider=provider,
        abstention_policy=policy(),
    )

    generation = service.generate_with_metadata(
        question="Question?",
        retrieval_results=[result()],
    )

    assert generation.answer.answerability is Answerability.ANSWERABLE
    assert generation.model_name == "recording-answer-model"
    assert generation.provider_request_id == "recording-request-id"
    assert generation.usage == ModelUsage(
        input_tokens=10,
        output_tokens=4,
        total_tokens=14,
    )
    assert provider.calls == 1
