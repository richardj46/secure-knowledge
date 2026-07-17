from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class RegressionLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maximum_recall_drop: float = Field(default=0.02, ge=0.0)
    maximum_groundedness_drop: float = Field(default=0.02, ge=0.0)
    maximum_latency_increase_ratio: float = Field(default=0.25, ge=0.0)
    maximum_cost_increase_ratio: float = Field(default=0.25, ge=0.0)


@dataclass(frozen=True)
class MetricDelta:
    baseline_value: float
    current_value: float
    delta: float
    increase_ratio: float | None
    passed: bool | None
    limit: float | None
    comparison: str | None


@dataclass(frozen=True)
class BaselineComparison:
    deltas: dict[str, MetricDelta]
    passed: bool


REQUIRED_BASELINE_METRICS = frozenset(
    {
        "authorization_leakage_rate",
        "document_recall@5",
        "groundedness",
        "unsafe_answer_rate",
        "p95_latency",
        "average_cost",
    }
)


def compare_to_baseline(
    *,
    baseline: dict[str, float],
    current: dict[str, float],
    limits: RegressionLimits,
) -> BaselineComparison:
    missing_metrics = REQUIRED_BASELINE_METRICS - baseline.keys()
    missing_metrics |= REQUIRED_BASELINE_METRICS - current.keys()
    if missing_metrics:
        names = ", ".join(sorted(missing_metrics))
        raise ValueError(f"Missing baseline comparison metrics: {names}")

    deltas = {
        "document_recall_at_5": _maximum_drop_delta(
            baseline=baseline["document_recall@5"],
            current=current["document_recall@5"],
            limit=limits.maximum_recall_drop,
        ),
        "groundedness": _maximum_drop_delta(
            baseline=baseline["groundedness"],
            current=current["groundedness"],
            limit=limits.maximum_groundedness_drop,
        ),
        "unsafe_answer_rate": _informational_delta(
            baseline=baseline["unsafe_answer_rate"],
            current=current["unsafe_answer_rate"],
        ),
        "p95_latency_ms": _maximum_increase_ratio_delta(
            baseline=baseline["p95_latency"],
            current=current["p95_latency"],
            limit=limits.maximum_latency_increase_ratio,
        ),
        "average_cost_microusd": _maximum_increase_ratio_delta(
            baseline=baseline["average_cost"],
            current=current["average_cost"],
            limit=limits.maximum_cost_increase_ratio,
        ),
    }
    authorization_passed = current["authorization_leakage_rate"] == 0.0
    regression_metrics_passed = all(
        delta.passed is not False for delta in deltas.values()
    )
    return BaselineComparison(
        deltas=deltas,
        passed=authorization_passed and regression_metrics_passed,
    )


def _maximum_drop_delta(
    *,
    baseline: float,
    current: float,
    limit: float,
) -> MetricDelta:
    delta = current - baseline
    return MetricDelta(
        baseline_value=baseline,
        current_value=current,
        delta=delta,
        increase_ratio=None,
        passed=delta >= -limit,
        limit=limit,
        comparison="maximum_drop",
    )


def _maximum_increase_ratio_delta(
    *,
    baseline: float,
    current: float,
    limit: float,
) -> MetricDelta:
    if baseline == 0.0:
        increase_ratio = 0.0 if current <= 0.0 else None
        passed = current <= 0.0
    else:
        increase_ratio = (current - baseline) / baseline
        passed = increase_ratio <= limit

    return MetricDelta(
        baseline_value=baseline,
        current_value=current,
        delta=current - baseline,
        increase_ratio=increase_ratio,
        passed=passed,
        limit=limit,
        comparison="maximum_increase_ratio",
    )


def _informational_delta(
    *,
    baseline: float,
    current: float,
) -> MetricDelta:
    return MetricDelta(
        baseline_value=baseline,
        current_value=current,
        delta=current - baseline,
        increase_ratio=None,
        passed=None,
        limit=None,
        comparison=None,
    )
