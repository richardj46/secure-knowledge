from uuid import uuid4

import pytest
from pydantic import ValidationError

from secure_knowledge_core.answers.schemas import CitationDraft, GeneratedAnswer
from secure_knowledge_core.database.enums import Answerability


def test_answerable_result_rejects_blank_answer() -> None:
    with pytest.raises(ValidationError, match="must include an answer"):
        GeneratedAnswer(
            answer="   ",
            answerability=Answerability.ANSWERABLE,
            confidence=0.9,
            citations=[
                CitationDraft(
                    chunk_id=uuid4(),
                    claims=["Supported claim."],
                )
            ],
        )


def test_citation_rejects_more_than_ten_claims() -> None:
    with pytest.raises(ValidationError):
        CitationDraft(
            chunk_id=uuid4(),
            claims=[f"Claim {index}" for index in range(11)],
        )


def test_generated_answer_rejects_more_than_twenty_citations() -> None:
    with pytest.raises(ValidationError):
        GeneratedAnswer(
            answer="Supported answer.",
            answerability=Answerability.ANSWERABLE,
            confidence=0.9,
            citations=[
                CitationDraft(
                    chunk_id=uuid4(),
                    claims=["Supported claim."],
                )
                for _ in range(21)
            ],
        )
