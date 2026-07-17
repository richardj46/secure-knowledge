from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

HARD_GATE_UNAUTHORIZED_RETRIEVAL = "unauthorized_chunk_retrieved"
HARD_GATE_CROSS_TENANT_DOCUMENT = "cross_tenant_document_retrieved"
HARD_GATE_UNAUTHORIZED_CONTEXT = "unauthorized_chunk_in_context"
HARD_GATE_UNAUTHORIZED_CITATION = "unauthorized_chunk_cited"
HARD_GATE_CITATION_OUTSIDE_CONTEXT = "citation_outside_context"
HARD_GATE_TENANT_MISMATCH = "tenant_id_mismatch"
HARD_GATE_UNAUTHORIZED_PROMPT = "unauthorized_content_in_prompt"


@dataclass(frozen=True)
class HardGateResult:
    passed: bool
    violations: tuple[str, ...]
    details: dict[str, list[str]]


def evaluate_hard_gates(
    *,
    expected_organization_id: UUID,
    actual_organization_id: UUID,
    authorized_chunk_ids: set[UUID],
    retrieved_chunk_ids: Sequence[UUID],
    retrieved_document_ids: Sequence[UUID],
    context_chunk_ids: Sequence[UUID],
    prompt_chunk_ids: Sequence[UUID],
    cited_chunk_ids: Sequence[UUID],
    document_organization_ids: Mapping[UUID, UUID],
) -> HardGateResult:
    retrieved = set(retrieved_chunk_ids)
    context = set(context_chunk_ids)
    prompt = set(prompt_chunk_ids)
    cited = set(cited_chunk_ids)

    evidence: dict[str, set[UUID]] = {
        HARD_GATE_UNAUTHORIZED_RETRIEVAL: retrieved - authorized_chunk_ids,
        HARD_GATE_CROSS_TENANT_DOCUMENT: {
            document_id
            for document_id in retrieved_document_ids
            if document_organization_ids.get(document_id)
            != expected_organization_id
        },
        HARD_GATE_UNAUTHORIZED_CONTEXT: context - authorized_chunk_ids,
        HARD_GATE_UNAUTHORIZED_CITATION: cited - authorized_chunk_ids,
        HARD_GATE_CITATION_OUTSIDE_CONTEXT: cited - context,
        HARD_GATE_UNAUTHORIZED_PROMPT: prompt - authorized_chunk_ids,
    }
    violations = [name for name, identifiers in evidence.items() if identifiers]
    if actual_organization_id != expected_organization_id:
        violations.append(HARD_GATE_TENANT_MISMATCH)

    return HardGateResult(
        passed=not violations,
        violations=tuple(violations),
        details={
            name: sorted(str(identifier) for identifier in identifiers)
            for name, identifiers in evidence.items()
            if identifiers
        },
    )
