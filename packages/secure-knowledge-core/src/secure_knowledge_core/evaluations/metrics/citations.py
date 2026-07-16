from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _validate_score(name: str, value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1.")


@dataclass(frozen=True)
class AnswerQualityMetrics:
    citation_validity: float
    citation_coverage: float
    citation_correctness: float
    groundedness: float | None
    answer_relevance: float | None
    completeness: float | None


def score_answer_quality(
    *,
    cited_chunk_ids: Sequence[UUID],
    allowed_chunk_ids: set[UUID],
    expected_relevant_chunk_ids: set[UUID],
    factual_claim_count: int,
    supported_claim_count: int,
    groundedness: float | None = None,
    answer_relevance: float | None = None,
    completeness: float | None = None,
) -> AnswerQualityMetrics:
    if factual_claim_count < 0 or supported_claim_count < 0:
        raise ValueError("Claim counts must not be negative.")
    if supported_claim_count > factual_claim_count:
        raise ValueError("Supported claims cannot exceed factual claims.")
    _validate_score("groundedness", groundedness)
    _validate_score("answer_relevance", answer_relevance)
    _validate_score("completeness", completeness)

    citation_count = len(cited_chunk_ids)
    empty_citation_score = 1.0 if factual_claim_count == 0 else 0.0
    citation_validity = (
        _safe_ratio(
            sum(chunk_id in allowed_chunk_ids for chunk_id in cited_chunk_ids),
            citation_count,
        )
        if citation_count
        else empty_citation_score
    )
    citation_correctness = (
        _safe_ratio(
            sum(
                chunk_id in expected_relevant_chunk_ids
                for chunk_id in cited_chunk_ids
            ),
            citation_count,
        )
        if citation_count
        else empty_citation_score
    )
    citation_coverage = (
        supported_claim_count / factual_claim_count
        if factual_claim_count
        else 1.0
    )

    return AnswerQualityMetrics(
        citation_validity=citation_validity,
        citation_coverage=citation_coverage,
        citation_correctness=citation_correctness,
        groundedness=groundedness,
        answer_relevance=answer_relevance,
        completeness=completeness,
    )
