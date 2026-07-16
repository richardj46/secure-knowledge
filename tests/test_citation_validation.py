from uuid import UUID, uuid4

import pytest

from secure_knowledge_core.database.enums import Answerability
from secure_knowledge_core.llm.citations import validate_citations
from secure_knowledge_core.llm.exceptions import CitationValidationError
from secure_knowledge_core.llm.schemas import CitationDraft, GeneratedAnswer


def generated_answer(
    *,
    answerability: Answerability,
    chunk_ids: list[UUID],
) -> GeneratedAnswer:
    return GeneratedAnswer(
        answer="A supported answer.",
        answerability=answerability,
        confidence=0.8,
        citations=[
            CitationDraft(chunk_id=chunk_id, claims=["Supported claim."])
            for chunk_id in chunk_ids
        ],
    )


def test_valid_citations_are_accepted() -> None:
    chunk_id = uuid4()
    answer = generated_answer(
        answerability=Answerability.ANSWERABLE,
        chunk_ids=[chunk_id],
    )

    validate_citations(answer=answer, allowed_chunk_ids={chunk_id})


def test_unknown_citation_is_rejected() -> None:
    answer = generated_answer(
        answerability=Answerability.ANSWERABLE,
        chunk_ids=[uuid4()],
    )

    with pytest.raises(CitationValidationError, match="Unknown citation chunk"):
        validate_citations(answer=answer, allowed_chunk_ids={uuid4()})


def test_duplicate_chunk_citation_is_rejected() -> None:
    chunk_id = uuid4()
    answer = generated_answer(
        answerability=Answerability.ANSWERABLE,
        chunk_ids=[chunk_id, chunk_id],
    )

    with pytest.raises(CitationValidationError, match="Duplicate citation chunk"):
        validate_citations(answer=answer, allowed_chunk_ids={chunk_id})


def test_answerable_response_requires_a_valid_citation() -> None:
    answer = generated_answer(
        answerability=Answerability.ANSWERABLE,
        chunk_ids=[],
    )

    with pytest.raises(CitationValidationError, match="must include"):
        validate_citations(answer=answer, allowed_chunk_ids=set())


def test_not_found_response_rejects_citations() -> None:
    chunk_id = uuid4()
    answer = generated_answer(
        answerability=Answerability.NOT_FOUND,
        chunk_ids=[chunk_id],
    )

    with pytest.raises(CitationValidationError, match="cannot include"):
        validate_citations(answer=answer, allowed_chunk_ids={chunk_id})
