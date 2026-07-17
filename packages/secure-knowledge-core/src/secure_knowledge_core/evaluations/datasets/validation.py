from pathlib import Path
from typing import Any

from pydantic import ValidationError

from secure_knowledge_core.evaluations.datasets.schemas import (
    EvaluationCaseDefinition,
)


class EvaluationDatasetValidationError(ValueError):
    """Raised when an evaluation dataset contains an invalid record."""


def validate_record(
    value: Any,
    *,
    path: Path,
    line_number: int,
) -> EvaluationCaseDefinition:
    if not isinstance(value, dict):
        raise EvaluationDatasetValidationError(
            f"{path}:{line_number}: each JSONL line must contain an object."
        )

    try:
        return EvaluationCaseDefinition.model_validate(value)
    except ValidationError as exc:
        raise EvaluationDatasetValidationError(
            f"{path}:{line_number}: invalid evaluation case: {exc}"
        ) from exc
