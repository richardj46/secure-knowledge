from uuid import UUID

from secure_knowledge_core.database.enums import Answerability
from secure_knowledge_core.llm.exceptions import CitationValidationError
from secure_knowledge_core.llm.schemas import GeneratedAnswer


def validate_citations(
    *,
    answer: GeneratedAnswer,
    allowed_chunk_ids: set[UUID],
) -> None:
    cited_chunk_ids: set[UUID] = set()

    for citation in answer.citations:
        if citation.chunk_id not in allowed_chunk_ids:
            raise CitationValidationError(
                f"Unknown citation chunk: {citation.chunk_id}"
            )
        if citation.chunk_id in cited_chunk_ids:
            raise CitationValidationError(
                f"Duplicate citation chunk: {citation.chunk_id}"
            )

        cited_chunk_ids.add(citation.chunk_id)

    if answer.answerability in {
        Answerability.ANSWERABLE,
        Answerability.PARTIALLY_ANSWERABLE,
    } and not cited_chunk_ids:
        raise CitationValidationError(
            "An answerable response must include at least one valid citation."
        )

    if answer.answerability is Answerability.NOT_FOUND and cited_chunk_ids:
        raise CitationValidationError(
            "A not-found response cannot include factual citations."
        )
