from uuid import UUID

from secure_knowledge_core.answers.exceptions import CitationValidationError
from secure_knowledge_core.answers.schemas import GeneratedAnswer
from secure_knowledge_core.database.enums import Answerability


def validate_generated_answer(
    *,
    generated: GeneratedAnswer,
    allowed_chunk_ids: set[UUID],
) -> None:
    cited_chunk_ids: set[UUID] = set()

    for citation in generated.citations:
        if citation.chunk_id not in allowed_chunk_ids:
            raise CitationValidationError(
                f"Unknown citation chunk: {citation.chunk_id}"
            )

        if citation.chunk_id in cited_chunk_ids:
            raise CitationValidationError(
                f"Duplicate citation chunk: {citation.chunk_id}"
            )

        cited_chunk_ids.add(citation.chunk_id)

    if generated.answerability in {
        Answerability.ANSWERABLE,
        Answerability.PARTIALLY_ANSWERABLE,
    }:
        if not generated.answer.strip():
            raise CitationValidationError(
                "An answerable response must contain an answer."
            )

        if not generated.citations:
            raise CitationValidationError(
                "An answerable response must include at least one valid citation."
            )

    if generated.answerability == Answerability.NOT_FOUND:
        if generated.citations:
            raise CitationValidationError(
                "A not-found response cannot include factual citations."
            )
