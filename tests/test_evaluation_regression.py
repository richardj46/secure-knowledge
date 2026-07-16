from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import pytest

from secure_knowledge_core.evaluations.datasets import load_jsonl_dataset
from secure_knowledge_core.evaluations.datasets.schemas import (
    EvaluationCaseDefinition,
)
from secure_knowledge_core.evaluations.graders.deterministic import (
    grade_forbidden_claims,
    grade_required_claims,
)
from secure_knowledge_core.evaluations.metrics.authorization import (
    score_authorization_safety,
)
from secure_knowledge_core.evaluations.metrics.retrieval import recall_at_k
from secure_knowledge_core.evaluations.schemas import EvaluationRunCreate

DATASET_DIRECTORY = Path(__file__).resolve().parents[1] / "evaluation_datasets"
ORGANIZATION_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

INCIDENT_DOCUMENT_ID = UUID("10000000-0000-0000-0000-000000000001")
VPN_DOCUMENT_ID = UUID("10000000-0000-0000-0000-000000000002")
HANDBOOK_DOCUMENT_ID = UUID("10000000-0000-0000-0000-000000000003")
PAYROLL_DOCUMENT_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

INCIDENT_CHUNK_ID = UUID("20000000-0000-0000-0000-000000000001")
VPN_CHUNK_ID = UUID("20000000-0000-0000-0000-000000000002")
HANDBOOK_CHUNK_ID = UUID("20000000-0000-0000-0000-000000000003")
PAYROLL_CHUNK_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


@dataclass(frozen=True)
class DeterministicRetrievalFixture:
    retrieved_chunk_ids: list[UUID]
    context_chunk_ids: list[UUID]
    authorized_chunk_ids: set[UUID]
    chunk_document_ids: dict[UUID, UUID]
    chunk_organization_ids: dict[UUID, UUID]


@dataclass(frozen=True)
class DeterministicEvaluationResult:
    document_recall_at_5: float
    chunk_recall_at_5: float
    authorization_leakage_count: int


@dataclass(frozen=True)
class DeterministicAnswerFixture:
    answerability: str
    answer: str
    citation_count: int = 0


@dataclass(frozen=True)
class DeterministicAnswerResult:
    answerability_matches: bool
    required_claim_score: float
    forbidden_claims_passed: bool
    citation_count: int


class DeterministicEvaluationHarness:
    def __init__(
        self,
        fixtures: dict[str, DeterministicRetrievalFixture],
        answer_fixtures: dict[str, DeterministicAnswerFixture],
    ) -> None:
        self.fixtures = fixtures
        self.answer_fixtures = answer_fixtures

    def run_retrieval(
        self,
        case: EvaluationCaseDefinition,
    ) -> DeterministicEvaluationResult:
        fixture = self.fixtures.get(case.external_id)
        if fixture is None:
            document_ids = list(case.expected_document_ids)
            chunk_document_ids: dict[UUID, UUID] = {}
            if document_ids:
                chunk_document_ids = {
                    chunk_id: document_ids[min(index, len(document_ids) - 1)]
                    for index, chunk_id in enumerate(case.expected_chunk_ids)
                }
            fixture = DeterministicRetrievalFixture(
                retrieved_chunk_ids=list(case.expected_chunk_ids),
                context_chunk_ids=list(case.expected_chunk_ids),
                authorized_chunk_ids=set(case.expected_chunk_ids),
                chunk_document_ids=chunk_document_ids,
                chunk_organization_ids={
                    chunk_id: case.organization_id
                    for chunk_id in case.expected_chunk_ids
                },
            )
        retrieved_document_ids = [
            fixture.chunk_document_ids[chunk_id]
            for chunk_id in fixture.retrieved_chunk_ids
        ]
        authorization = score_authorization_safety(
            retrieved_chunk_ids=fixture.retrieved_chunk_ids,
            context_chunk_ids=fixture.context_chunk_ids,
            authorized_chunk_ids=fixture.authorized_chunk_ids,
            chunk_document_ids=fixture.chunk_document_ids,
            chunk_organization_ids=fixture.chunk_organization_ids,
            expected_organization_id=case.organization_id,
            forbidden_document_ids=set(case.forbidden_document_ids),
            forbidden_chunk_ids=set(case.forbidden_chunk_ids),
        )
        leakage_count = sum(
            (
                int(authorization.unauthorized_retrieval_rate > 0),
                int(authorization.unauthorized_context_rate > 0),
                authorization.cross_tenant_leakage_count,
                authorization.forbidden_document_hit_count,
                authorization.forbidden_chunk_hit_count,
            )
        )

        return DeterministicEvaluationResult(
            document_recall_at_5=recall_at_k(
                retrieved_ids=retrieved_document_ids,
                expected_ids=set(case.expected_document_ids),
                k=5,
            ),
            chunk_recall_at_5=recall_at_k(
                retrieved_ids=fixture.retrieved_chunk_ids,
                expected_ids=set(case.expected_chunk_ids),
                k=5,
            ),
            authorization_leakage_count=leakage_count,
        )

    def run_answer(
        self,
        case: EvaluationCaseDefinition,
    ) -> DeterministicAnswerResult:
        fixture = self.answer_fixtures.get(case.external_id)
        if fixture is None:
            fixture = DeterministicAnswerFixture(
                answerability=case.expected_answerability.value,
                answer=(
                    " ".join(case.required_claims)
                    or case.reference_answer
                    or "I could not find sufficient authorized evidence."
                ),
            )
        required_claims = grade_required_claims(
            answer=fixture.answer,
            required_claims=case.required_claims,
        )
        forbidden_claims = grade_forbidden_claims(
            answer=fixture.answer,
            forbidden_claims=case.forbidden_claims,
        )

        return DeterministicAnswerResult(
            answerability_matches=(
                fixture.answerability == case.expected_answerability.value
            ),
            required_claim_score=required_claims.score,
            forbidden_claims_passed=forbidden_claims.passed,
            citation_count=fixture.citation_count,
        )


@pytest.fixture
def evaluation_harness() -> DeterministicEvaluationHarness:
    return DeterministicEvaluationHarness(
        fixtures={
            "retrieval-incident-escalation": DeterministicRetrievalFixture(
                retrieved_chunk_ids=[INCIDENT_CHUNK_ID, HANDBOOK_CHUNK_ID],
                context_chunk_ids=[INCIDENT_CHUNK_ID],
                authorized_chunk_ids={INCIDENT_CHUNK_ID, HANDBOOK_CHUNK_ID},
                chunk_document_ids={
                    INCIDENT_CHUNK_ID: INCIDENT_DOCUMENT_ID,
                    HANDBOOK_CHUNK_ID: HANDBOOK_DOCUMENT_ID,
                },
                chunk_organization_ids={
                    INCIDENT_CHUNK_ID: ORGANIZATION_ID,
                    HANDBOOK_CHUNK_ID: ORGANIZATION_ID,
                },
            ),
            "retrieval-vpn-reset": DeterministicRetrievalFixture(
                retrieved_chunk_ids=[VPN_CHUNK_ID, HANDBOOK_CHUNK_ID],
                context_chunk_ids=[VPN_CHUNK_ID],
                authorized_chunk_ids={VPN_CHUNK_ID, HANDBOOK_CHUNK_ID},
                chunk_document_ids={
                    VPN_CHUNK_ID: VPN_DOCUMENT_ID,
                    HANDBOOK_CHUNK_ID: HANDBOOK_DOCUMENT_ID,
                },
                chunk_organization_ids={
                    VPN_CHUNK_ID: ORGANIZATION_ID,
                    HANDBOOK_CHUNK_ID: ORGANIZATION_ID,
                },
            ),
            "auth-001": DeterministicRetrievalFixture(
                retrieved_chunk_ids=[HANDBOOK_CHUNK_ID],
                context_chunk_ids=[],
                authorized_chunk_ids={HANDBOOK_CHUNK_ID},
                chunk_document_ids={
                    HANDBOOK_CHUNK_ID: HANDBOOK_DOCUMENT_ID,
                    PAYROLL_CHUNK_ID: PAYROLL_DOCUMENT_ID,
                },
                chunk_organization_ids={
                    HANDBOOK_CHUNK_ID: ORGANIZATION_ID,
                    PAYROLL_CHUNK_ID: ORGANIZATION_ID,
                },
            ),
        },
        answer_fixtures={
            "abstention-unknown-benefit": DeterministicAnswerFixture(
                answerability="not_found",
                answer="I could not find authorized evidence for that policy.",
            ),
            "grounding-incident-escalation": DeterministicAnswerFixture(
                answerability="answerable",
                answer="Critical incidents must be escalated immediately.",
            ),
        },
    )


@pytest.mark.evaluation
@pytest.mark.parametrize(
    "case",
    load_jsonl_dataset(DATASET_DIRECTORY / "retrieval_basic.jsonl"),
    ids=lambda case: case.external_id,
)
def test_retrieval_case(
    case: EvaluationCaseDefinition,
    evaluation_harness: DeterministicEvaluationHarness,
) -> None:
    result = evaluation_harness.run_retrieval(case)

    assert result.authorization_leakage_count == 0
    assert result.document_recall_at_5 == 1.0
    assert result.chunk_recall_at_5 == 1.0


@pytest.mark.evaluation
@pytest.mark.security
@pytest.mark.parametrize(
    "case",
    load_jsonl_dataset(DATASET_DIRECTORY / "authorization_leakage.jsonl"),
    ids=lambda case: case.external_id,
)
def test_authorization_case(
    case: EvaluationCaseDefinition,
    evaluation_harness: DeterministicEvaluationHarness,
) -> None:
    result = evaluation_harness.run_retrieval(case)

    assert result.authorization_leakage_count == 0


@pytest.mark.evaluation
@pytest.mark.security
def test_salary_information_is_not_answered_from_forbidden_payroll(
    evaluation_harness: DeterministicEvaluationHarness,
) -> None:
    cases = load_jsonl_dataset(
        DATASET_DIRECTORY / "authorization_leakage.jsonl"
    )
    case = next(
        item
        for item in cases
        if item.external_id == "auth-salary-exists-but-forbidden"
    )

    retrieval = evaluation_harness.run_retrieval(case)
    answer = evaluation_harness.run_answer(case)

    assert retrieval.authorization_leakage_count == 0
    assert answer.answerability_matches
    assert answer.forbidden_claims_passed
    assert answer.citation_count == case.expected_citation_count
    assert case.expected_answerability.value == "not_found"
    assert case.expected_citation_count == 0
    assert case.authorized_evidence_texts == [
        "Employee benefits include private health insurance."
    ]
    assert case.forbidden_evidence_texts == [
        "Alice earns €150,000 annually."
    ]


@pytest.mark.evaluation
@pytest.mark.parametrize(
    "case",
    [
        *load_jsonl_dataset(DATASET_DIRECTORY / "abstention.jsonl"),
        *load_jsonl_dataset(DATASET_DIRECTORY / "answer_grounding.jsonl"),
    ],
    ids=lambda case: case.external_id,
)
def test_answer_case(
    case: EvaluationCaseDefinition,
    evaluation_harness: DeterministicEvaluationHarness,
) -> None:
    result = evaluation_harness.run_answer(case)

    assert result.answerability_matches
    assert result.required_claim_score == 1.0
    assert result.forbidden_claims_passed


@pytest.mark.evaluation
def test_default_run_configuration_is_ci_safe() -> None:
    configuration = EvaluationRunCreate().build_configuration(
        default_answer_model="external-answer-model",
        default_embedding_model="external-embedding-model",
    )

    assert configuration["mode"] == "deterministic"
    assert configuration["include_model_graders"] is False
    assert configuration["embedding_model"] == "fixed"
    assert configuration["answer_model"] == "fake-answer-model"
    assert configuration["mode_policy"]["uses_external_providers"] is False
    assert configuration["mode_policy"]["ci_safe"] is True
