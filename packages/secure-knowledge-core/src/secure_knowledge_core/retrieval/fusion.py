import re
from dataclasses import dataclass
from uuid import UUID

from secure_knowledge_core.retrieval.repository import RankedChunk


@dataclass
class FusedChunk:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    page_number: int | None
    section_title: str | None
    fused_score: float = 0.0
    vector_rank: int | None = None
    keyword_rank: int | None = None
    vector_score: float | None = None
    keyword_score: float | None = None


def normalize_for_deduplication(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def deduplicate_results(
    results: list[FusedChunk],
) -> list[FusedChunk]:
    seen: set[str] = set()
    deduplicated: list[FusedChunk] = []

    for result in results:
        normalized = normalize_for_deduplication(result.content)

        if normalized in seen:
            continue

        seen.add(normalized)
        deduplicated.append(result)

    return deduplicated


def reciprocal_rank_fusion(
    *,
    vector_results: list[RankedChunk],
    keyword_results: list[RankedChunk],
    k: int = 60,
) -> list[FusedChunk]:
    fused: dict[UUID, FusedChunk] = {}

    for result in vector_results:
        item = fused.setdefault(
            result.chunk_id,
            FusedChunk(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                document_title=result.document_title,
                content=result.content,
                page_number=result.page_number,
                section_title=result.section_title,
            ),
        )

        item.vector_rank = result.rank
        item.vector_score = result.score
        item.fused_score += 1.0 / (k + result.rank)

    for result in keyword_results:
        item = fused.setdefault(
            result.chunk_id,
            FusedChunk(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                document_title=result.document_title,
                content=result.content,
                page_number=result.page_number,
                section_title=result.section_title,
            ),
        )

        item.keyword_rank = result.rank
        item.keyword_score = result.score
        item.fused_score += 1.0 / (k + result.rank)

    return sorted(
        fused.values(),
        key=lambda item: item.fused_score,
        reverse=True,
    )
