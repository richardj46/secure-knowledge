import re
from dataclasses import dataclass
from uuid import UUID

from secure_knowledge_core.retrieval.schemas import RetrievalResult


@dataclass(frozen=True)
class ContextPassage:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    page_number: int | None
    content: str


def build_context_passages(
    retrieval_results: list[RetrievalResult],
) -> list[ContextPassage]:
    return [
        ContextPassage(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            document_title=result.document_title,
            page_number=result.page_number,
            content=result.content,
        )
        for result in retrieval_results
    ]


def format_prompt_context(passages: list[ContextPassage]) -> str:
    return "\n\n".join(_format_passage(passage) for passage in passages)


def _format_passage(passage: ContextPassage) -> str:
    document_title = re.sub(r"\s+", " ", passage.document_title).strip()
    page_number = str(passage.page_number) if passage.page_number is not None else "N/A"
    return (
        f"[CHUNK_ID: {passage.chunk_id}]\n"
        f"Document: {document_title}\n"
        f"Page: {page_number}\n"
        f"Content:\n{passage.content}"
    )
