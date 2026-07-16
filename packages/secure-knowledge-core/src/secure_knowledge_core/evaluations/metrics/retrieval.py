from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RetrievalQualityMetrics:
    hit_rate_at_k: float
    recall_at_k: float
    precision_at_k: float
    mean_reciprocal_rank: float


def hit_rate_at_k(
    *,
    retrieved_ids: list[UUID],
    expected_ids: set[UUID],
    k: int,
) -> float:
    if not expected_ids:
        return 1.0 if not retrieved_ids[:k] else 0.0

    return float(
        bool(set(retrieved_ids[:k]) & expected_ids)
    )


def recall_at_k(
    *,
    retrieved_ids: list[UUID],
    expected_ids: set[UUID],
    k: int,
) -> float:
    if not expected_ids:
        return 1.0

    found = set(retrieved_ids[:k]) & expected_ids
    return len(found) / len(expected_ids)


def precision_at_k(
    *,
    retrieved_ids: list[UUID],
    expected_ids: set[UUID],
    k: int,
) -> float:
    selected = retrieved_ids[:k]

    if not selected:
        return 1.0 if not expected_ids else 0.0

    relevant = set(selected) & expected_ids
    return len(relevant) / len(selected)


def reciprocal_rank(
    *,
    retrieved_ids: list[UUID],
    expected_ids: set[UUID],
) -> float:
    for rank, item_id in enumerate(
        retrieved_ids,
        start=1,
    ):
        if item_id in expected_ids:
            return 1.0 / rank

    return 0.0


def score_retrieval_quality(
    *,
    ranked_chunk_ids: list[UUID],
    expected_relevant_chunk_ids: set[UUID],
    k: int,
) -> RetrievalQualityMetrics:
    if k < 1:
        raise ValueError("k must be at least 1.")

    return RetrievalQualityMetrics(
        hit_rate_at_k=hit_rate_at_k(
            retrieved_ids=ranked_chunk_ids,
            expected_ids=expected_relevant_chunk_ids,
            k=k,
        ),
        recall_at_k=recall_at_k(
            retrieved_ids=ranked_chunk_ids,
            expected_ids=expected_relevant_chunk_ids,
            k=k,
        ),
        precision_at_k=precision_at_k(
            retrieved_ids=ranked_chunk_ids,
            expected_ids=expected_relevant_chunk_ids,
            k=k,
        ),
        mean_reciprocal_rank=reciprocal_rank(
            retrieved_ids=ranked_chunk_ids,
            expected_ids=expected_relevant_chunk_ids,
        ),
    )
