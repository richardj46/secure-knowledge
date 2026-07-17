from uuid import uuid4

from secure_knowledge_core.answers.context import ContextPassage
from secure_knowledge_core.answers.schemas import CitationDraft, GeneratedAnswer
from secure_knowledge_core.answers.validation import validate_generated_answer
from secure_knowledge_core.database.enums import Answerability
from secure_knowledge_core.llm.fake import FakeAnswerProvider
from secure_knowledge_core.llm.interface import ModelUsage


def test_fake_provider_answers_only_from_approved_context() -> None:
    passage = ContextPassage(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Incident Response Guide",
        page_number=7,
        content="Critical incidents must be escalated immediately.",
    )

    generated = GeneratedAnswer(
        answer=passage.content,
        answerability=Answerability.ANSWERABLE,
        confidence=0.75,
        citations=[
            CitationDraft(
                chunk_id=passage.chunk_id,
                claims=[passage.content],
            )
        ],
        limitations=[],
    )
    provider = FakeAnswerProvider(generated)

    result = provider.generate_answer(
        question="How should a critical incident be escalated?",
        context=[passage],
    )
    answer = result.generated_answer

    assert answer.answer == passage.content
    assert answer.answerability is Answerability.ANSWERABLE
    assert [citation.chunk_id for citation in answer.citations] == [
        passage.chunk_id
    ]
    validate_generated_answer(
        generated=answer,
        allowed_chunk_ids={passage.chunk_id},
    )
    assert provider.received_question == (
        "How should a critical incident be escalated?"
    )
    assert provider.received_context == [passage]


def test_fake_provider_abstains_without_approved_context() -> None:
    generated = GeneratedAnswer(
        answer="I couldn't find sufficient supporting information.",
        answerability=Answerability.NOT_FOUND,
        confidence=1.0,
        citations=[],
        limitations=["No approved context was supplied."],
    )
    result = FakeAnswerProvider(generated).generate_answer(
        question="Question without evidence",
        context=[],
    )
    answer = result.generated_answer

    assert answer.answerability is Answerability.NOT_FOUND
    assert answer.citations == []


def test_fake_provider_returns_injected_structured_answer() -> None:
    authorized_chunk_id = uuid4()
    generated = GeneratedAnswer(
        answer="Critical incidents must be escalated immediately.",
        answerability=Answerability.ANSWERABLE,
        confidence=0.9,
        citations=[
            CitationDraft(
                chunk_id=authorized_chunk_id,
                claims=[
                    "Critical incidents require immediate escalation."
                ],
            )
        ],
        limitations=[],
    )

    provider = FakeAnswerProvider(generated)
    result = provider.generate_answer(
        question="How should a critical incident be escalated?",
        context=[],
    )

    assert result.generated_answer is generated
    assert result.model_name == "fake-answer-model"
    assert result.provider_request_id == "fake-request-id"
    assert result.usage == ModelUsage(
        input_tokens=100,
        output_tokens=30,
        total_tokens=130,
    )
