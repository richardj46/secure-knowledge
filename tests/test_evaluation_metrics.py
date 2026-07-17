from uuid import uuid4

import pytest

from secure_knowledge_core.evaluations.metrics import (
    AnswerabilityObservation,
    OperationalObservation,
    RegressionLimits,
    compare_to_baseline,
    score_abstention_quality,
    score_answer_quality,
    score_authorization_safety,
    score_operational_quality,
    score_retrieval_quality,
)

pytestmark = pytest.mark.evaluation


def test_retrieval_quality_metrics() -> None:
    relevant_one = uuid4()
    relevant_two = uuid4()
    relevant_three = uuid4()

    metrics = score_retrieval_quality(
        ranked_chunk_ids=[uuid4(), relevant_one, relevant_two],
        expected_relevant_chunk_ids={
            relevant_one,
            relevant_two,
            relevant_three,
        },
        k=3,
    )

    assert metrics.hit_rate_at_k == 1.0
    assert metrics.recall_at_k == pytest.approx(2 / 3)
    assert metrics.precision_at_k == pytest.approx(2 / 3)
    assert metrics.mean_reciprocal_rank == 0.5


def test_authorization_metrics_detect_cross_tenant_leakage() -> None:
    organization_id = uuid4()
    other_organization_id = uuid4()
    authorized_chunk_id = uuid4()
    forbidden_chunk_id = uuid4()
    authorized_document_id = uuid4()
    forbidden_document_id = uuid4()

    metrics = score_authorization_safety(
        retrieved_chunk_ids=[authorized_chunk_id, forbidden_chunk_id],
        context_chunk_ids=[forbidden_chunk_id],
        authorized_chunk_ids={authorized_chunk_id},
        chunk_document_ids={
            authorized_chunk_id: authorized_document_id,
            forbidden_chunk_id: forbidden_document_id,
        },
        chunk_organization_ids={
            authorized_chunk_id: organization_id,
            forbidden_chunk_id: other_organization_id,
        },
        expected_organization_id=organization_id,
        forbidden_document_ids={forbidden_document_id},
        forbidden_chunk_ids={forbidden_chunk_id},
    )

    assert metrics.unauthorized_retrieval_rate == 0.5
    assert metrics.unauthorized_context_rate == 1.0
    assert metrics.cross_tenant_leakage_count == 1
    assert metrics.forbidden_document_hit_count == 1
    assert metrics.forbidden_chunk_hit_count == 1


def test_answer_quality_combines_deterministic_and_external_grades() -> None:
    relevant_chunk_id = uuid4()
    invented_chunk_id = uuid4()

    metrics = score_answer_quality(
        cited_chunk_ids=[relevant_chunk_id, invented_chunk_id],
        allowed_chunk_ids={relevant_chunk_id},
        expected_relevant_chunk_ids={relevant_chunk_id},
        factual_claim_count=4,
        supported_claim_count=2,
        groundedness=0.75,
        answer_relevance=0.8,
        completeness=0.6,
    )

    assert metrics.citation_validity == 0.5
    assert metrics.citation_coverage == 0.5
    assert metrics.citation_correctness == 0.5
    assert metrics.groundedness == 0.75
    assert metrics.answer_relevance == 0.8
    assert metrics.completeness == 0.6


def test_abstention_metrics_include_answerable_f1() -> None:
    metrics = score_abstention_quality(
        [
            AnswerabilityObservation(True, True),
            AnswerabilityObservation(False, False),
            AnswerabilityObservation(False, True),
            AnswerabilityObservation(True, False),
        ]
    )

    assert metrics.correct_abstention_rate == 0.5
    assert metrics.false_abstention_rate == 0.5
    assert metrics.unsafe_answer_rate == 0.5
    assert metrics.answerability_accuracy == 0.5
    assert metrics.answerable_precision == 0.5
    assert metrics.answerable_recall == 0.5
    assert metrics.answerable_f1 == 0.5


def test_operational_metrics_aggregate_latency_usage_cost_and_failures() -> None:
    metrics = score_operational_quality(
        [
            OperationalObservation(
                retrieval_latency_ms=10,
                generation_latency_ms=30,
                total_latency_ms=45,
                input_tokens=100,
                output_tokens=20,
                total_tokens=120,
                estimated_cost_microusd=50,
                provider_failed=False,
                retrieval_was_empty=False,
            ),
            OperationalObservation(
                retrieval_latency_ms=20,
                generation_latency_ms=None,
                total_latency_ms=25,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                estimated_cost_microusd=None,
                provider_failed=True,
                retrieval_was_empty=True,
            ),
        ]
    )

    assert metrics.mean_retrieval_latency_ms == 15.0
    assert metrics.mean_generation_latency_ms == 30.0
    assert metrics.mean_total_latency_ms == 35.0
    assert metrics.input_tokens == 100
    assert metrics.output_tokens == 20
    assert metrics.total_tokens == 120
    assert metrics.estimated_cost_microusd == 50
    assert metrics.provider_failure_rate == 0.5
    assert metrics.empty_retrieval_rate == 0.5


def test_baseline_comparison_calculates_deltas_and_regression_limits() -> None:
    comparison = compare_to_baseline(
        baseline={
            "document_recall@5": 0.86,
            "groundedness": 0.92,
            "unsafe_answer_rate": 0.01,
            "p95_latency": 4200.0,
            "average_cost": 2200.0,
            "authorization_leakage_rate": 0.0,
        },
        current={
            "document_recall@5": 0.82,
            "groundedness": 0.94,
            "unsafe_answer_rate": 0.03,
            "p95_latency": 5100.0,
            "average_cost": 1850.0,
            "authorization_leakage_rate": 0.0,
        },
        limits=RegressionLimits(),
    )

    assert comparison.deltas["document_recall_at_5"].delta == pytest.approx(-0.04)
    assert comparison.deltas["document_recall_at_5"].passed is False
    assert comparison.deltas["groundedness"].delta == pytest.approx(0.02)
    assert comparison.deltas["groundedness"].passed is True
    assert comparison.deltas["unsafe_answer_rate"].delta == pytest.approx(0.02)
    assert comparison.deltas["p95_latency_ms"].delta == 900.0
    assert comparison.deltas["p95_latency_ms"].passed is True
    assert comparison.deltas["average_cost_microusd"].delta == -350.0
    assert comparison.deltas["average_cost_microusd"].passed is True
    assert comparison.passed is False


def test_new_authorization_leakage_always_fails_baseline_comparison() -> None:
    values = {
        "document_recall@5": 1.0,
        "groundedness": 1.0,
        "unsafe_answer_rate": 0.0,
        "p95_latency": 100.0,
        "average_cost": 100.0,
        "authorization_leakage_rate": 0.0,
    }
    current = dict(values)
    current["authorization_leakage_rate"] = 0.01

    comparison = compare_to_baseline(
        baseline=values,
        current=current,
        limits=RegressionLimits(),
    )

    assert comparison.passed is False
