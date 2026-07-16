from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class EvaluationRunMode(StrEnum):
    DETERMINISTIC = "deterministic"
    FULL = "full"
    LIVE = "live"


@dataclass(frozen=True)
class EvaluationModePolicy:
    embedding_provider: str
    answer_provider: str
    model_grader_provider: str
    uses_external_providers: bool
    ci_safe: bool
    limited_dataset: bool

    def as_configuration(self) -> dict[str, Any]:
        return asdict(self)


MODE_POLICIES = {
    EvaluationRunMode.DETERMINISTIC: EvaluationModePolicy(
        embedding_provider="fake_or_fixed",
        answer_provider="fake",
        model_grader_provider="disabled",
        uses_external_providers=False,
        ci_safe=True,
        limited_dataset=False,
    ),
    EvaluationRunMode.FULL: EvaluationModePolicy(
        embedding_provider="configured",
        answer_provider="configured",
        model_grader_provider="configured",
        uses_external_providers=True,
        ci_safe=False,
        limited_dataset=False,
    ),
    EvaluationRunMode.LIVE: EvaluationModePolicy(
        embedding_provider="production",
        answer_provider="production",
        model_grader_provider="production",
        uses_external_providers=True,
        ci_safe=False,
        limited_dataset=True,
    ),
}


def get_mode_policy(mode: EvaluationRunMode) -> EvaluationModePolicy:
    return MODE_POLICIES[mode]
