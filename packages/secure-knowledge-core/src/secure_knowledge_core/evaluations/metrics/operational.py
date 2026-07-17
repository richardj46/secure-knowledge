from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


@dataclass(frozen=True)
class OperationalObservation:
    retrieval_latency_ms: int
    generation_latency_ms: int | None
    total_latency_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_microusd: int | None
    provider_failed: bool
    retrieval_was_empty: bool


@dataclass(frozen=True)
class OperationalQualityMetrics:
    mean_retrieval_latency_ms: float
    mean_generation_latency_ms: float | None
    mean_total_latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_microusd: int
    provider_failure_rate: float
    empty_retrieval_rate: float


def score_operational_quality(
    observations: Sequence[OperationalObservation],
) -> OperationalQualityMetrics:
    generation_latencies = [
        item.generation_latency_ms
        for item in observations
        if item.generation_latency_ms is not None
    ]

    return OperationalQualityMetrics(
        mean_retrieval_latency_ms=(
            fmean(item.retrieval_latency_ms for item in observations)
            if observations
            else 0.0
        ),
        mean_generation_latency_ms=(
            fmean(generation_latencies) if generation_latencies else None
        ),
        mean_total_latency_ms=(
            fmean(item.total_latency_ms for item in observations)
            if observations
            else 0.0
        ),
        input_tokens=sum(item.input_tokens for item in observations),
        output_tokens=sum(item.output_tokens for item in observations),
        total_tokens=sum(item.total_tokens for item in observations),
        estimated_cost_microusd=sum(
            item.estimated_cost_microusd or 0 for item in observations
        ),
        provider_failure_rate=_safe_ratio(
            sum(item.provider_failed for item in observations),
            len(observations),
        ),
        empty_retrieval_rate=_safe_ratio(
            sum(item.retrieval_was_empty for item in observations),
            len(observations),
        ),
    )
