from uuid import uuid4

from secure_knowledge_core.answers.context import ContextPassage
from secure_knowledge_core.answers.schemas import CitationDraft, GeneratedAnswer
from secure_knowledge_core.answers.validation import validate_generated_answer
from secure_knowledge_core.database.enums import Answerability
from secure_knowledge_core.llm.fake import FakeAnswerProvider


def test_fake_provider_answers_only_from_approved_context() -> None:
    passage = ContextPassage(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Incident Response Guide",
        page_number=7,
        content="Critical incidents must be escalated immediately.",
    )

    answer = FakeAnswerProvider().generate_answer(
        question="How should a critical incident be escalated?",
        context=[passage],
    )

    assert answer.answer == passage.content
    assert answer.answerability is Answerability.ANSWERABLE
    assert [citation.chunk_id for citation in answer.citations] == [
        passage.chunk_id
    ]
    validate_generated_answer(
        generated=answer,
        allowed_chunk_ids={passage.chunk_id},
    )


def test_fake_provider_abstains_without_approved_context() -> None:
    answer = FakeAnswerProvider().generate_answer(
        question="Question without evidence",
        context=[],
    )

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

    answer = FakeAnswerProvider(generated).generate_answer(
        question="How should a critical incident be escalated?",
        context=[],
    )

    assert answer is generated
