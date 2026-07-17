from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import mean

from secure_knowledge_core.database.enums import EvaluationCaseStatus
from secure_knowledge_core.database.models import EvaluationCaseResult

AVERAGED_CASE_METRICS = (
    "document_hit_rate@5",
    "document_recall@5",
    "document_recall@10",
    "chunk_recall@5",
    "chunk_recall@10",
    "mean_reciprocal_rank",
    "citation_validity",
    "citation_correctness",
    "groundedness",
    "answer_relevance",
    "answerability_accuracy",
    "unsafe_answer_rate",
    "false_abstention_rate",
    "authorization_leakage_rate",
)

PROVIDER_ERROR_CODES = {
    "provider_configuration_error",
    "provider_timeout",
    "provider_rate_limit",
    "provider_unavailable",
    "invalid_structured_output",
    "provider_refusal",
    "provider_error",
}


def average_metric(values: Sequence[float]) -> float:
    if not values:
        return 0.0

    return mean(values)


def percentile(values: Sequence[int], percentile_value: float) -> float:
    if not 0.0 <= percentile_value <= 1.0:
        raise ValueError("percentile_value must be between 0 and 1.")
    if not values:
        return 0.0

    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile_value
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower

    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


@dataclass(frozen=True)
class RunAggregateMetrics:
    values: dict[str, float]


def aggregate_run_metrics(
    *,
    case_results: Sequence[EvaluationCaseResult],
    case_metric_values: Mapping[str, Sequence[float]],
) -> RunAggregateMetrics:
    case_count = len(case_results)
    passed_count = sum(
        result.status == EvaluationCaseStatus.PASSED for result in case_results
    )
    latencies = [
        result.latency_ms
        for result in case_results
        if result.latency_ms is not None
    ]
    costs = [
        float(result.estimated_cost_microusd or 0) for result in case_results
    ]
    provider_error_count = sum(
        result.error_code in PROVIDER_ERROR_CODES for result in case_results
    )

    values = {
        metric_name: average_metric(case_metric_values.get(metric_name, ()))
        for metric_name in AVERAGED_CASE_METRICS
    }
    values.update(
        {
            "case_pass_rate": passed_count / case_count if case_count else 0.0,
            "p50_latency": percentile(latencies, 0.50),
            "p95_latency": percentile(latencies, 0.95),
            "average_cost": average_metric(costs),
            "total_cost": float(sum(costs)),
            "provider_error_rate": (
                provider_error_count / case_count if case_count else 0.0
            ),
        }
    )
    return RunAggregateMetrics(values=values)
