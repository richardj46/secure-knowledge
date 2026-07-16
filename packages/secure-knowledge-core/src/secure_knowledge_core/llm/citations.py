from uuid import UUID

from secure_knowledge_core.answers.schemas import GeneratedAnswer
from secure_knowledge_core.answers.validation import validate_generated_answer


def validate_citations(
    *,
    answer: GeneratedAnswer,
    allowed_chunk_ids: set[UUID],
) -> None:
    validate_generated_answer(
        generated=answer,
        allowed_chunk_ids=allowed_chunk_ids,
    )

__all__ = ["validate_citations"]
