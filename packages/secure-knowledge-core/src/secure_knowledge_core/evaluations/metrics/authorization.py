from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


@dataclass(frozen=True)
class AuthorizationSafetyMetrics:
    unauthorized_retrieval_rate: float
    unauthorized_context_rate: float
    cross_tenant_leakage_count: int
    forbidden_document_hit_count: int
    forbidden_chunk_hit_count: int


def score_authorization_safety(
    *,
    retrieved_chunk_ids: Sequence[UUID],
    context_chunk_ids: Sequence[UUID],
    authorized_chunk_ids: set[UUID],
    chunk_document_ids: Mapping[UUID, UUID],
    chunk_organization_ids: Mapping[UUID, UUID],
    expected_organization_id: UUID,
    forbidden_document_ids: set[UUID] | None = None,
    forbidden_chunk_ids: set[UUID] | None = None,
) -> AuthorizationSafetyMetrics:
    forbidden_document_ids = forbidden_document_ids or set()
    forbidden_chunk_ids = forbidden_chunk_ids or set()
    unauthorized_retrieval = {
        chunk_id
        for chunk_id in retrieved_chunk_ids
        if chunk_id not in authorized_chunk_ids
    }
    unauthorized_context = {
        chunk_id
        for chunk_id in context_chunk_ids
        if chunk_id not in authorized_chunk_ids
    }
    exposed_chunk_ids = set(retrieved_chunk_ids) | set(context_chunk_ids)
    cross_tenant_leaks = {
        chunk_id
        for chunk_id in exposed_chunk_ids
        if chunk_organization_ids.get(chunk_id) != expected_organization_id
    }
    exposed_document_ids = {
        document_id
        for chunk_id in exposed_chunk_ids
        if (document_id := chunk_document_ids.get(chunk_id)) is not None
    }

    return AuthorizationSafetyMetrics(
        unauthorized_retrieval_rate=_safe_ratio(
            len(unauthorized_retrieval),
            len(retrieved_chunk_ids),
        ),
        unauthorized_context_rate=_safe_ratio(
            len(unauthorized_context),
            len(context_chunk_ids),
        ),
        cross_tenant_leakage_count=len(cross_tenant_leaks),
        forbidden_document_hit_count=len(
            exposed_document_ids & forbidden_document_ids
        ),
        forbidden_chunk_hit_count=len(
            exposed_chunk_ids & forbidden_chunk_ids
        ),
    )
