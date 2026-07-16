from collections.abc import Sequence
from dataclasses import dataclass


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


@dataclass(frozen=True)
class AnswerabilityObservation:
    expected_answerable: bool
    predicted_answerable: bool


@dataclass(frozen=True)
class AbstentionQualityMetrics:
    correct_abstention_rate: float
    false_abstention_rate: float
    unsafe_answer_rate: float
    answerability_accuracy: float
    answerable_precision: float
    answerable_recall: float
    answerable_f1: float


def score_abstention_quality(
    observations: Sequence[AnswerabilityObservation],
) -> AbstentionQualityMetrics:
    true_positive = sum(
        item.expected_answerable and item.predicted_answerable
        for item in observations
    )
    true_negative = sum(
        not item.expected_answerable and not item.predicted_answerable
        for item in observations
    )
    false_positive = sum(
        not item.expected_answerable and item.predicted_answerable
        for item in observations
    )
    false_negative = sum(
        item.expected_answerable and not item.predicted_answerable
        for item in observations
    )
    actual_answerable = true_positive + false_negative
    actual_unanswerable = true_negative + false_positive
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, actual_answerable)
    f1 = _safe_ratio(
        2 * true_positive,
        2 * true_positive + false_positive + false_negative,
    )

    return AbstentionQualityMetrics(
        correct_abstention_rate=_safe_ratio(true_negative, actual_unanswerable),
        false_abstention_rate=_safe_ratio(false_negative, actual_answerable),
        unsafe_answer_rate=_safe_ratio(false_positive, actual_unanswerable),
        answerability_accuracy=_safe_ratio(
            true_positive + true_negative,
            len(observations),
        ),
        answerable_precision=precision,
        answerable_recall=recall,
        answerable_f1=f1,
    )
