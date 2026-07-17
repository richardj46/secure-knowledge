import json
from pathlib import Path

from pydantic import ValidationError

from secure_knowledge_core.evaluations.datasets.schemas import (
    EvaluationCaseDefinition,
)


class DatasetLoadError(Exception):
    pass


def load_jsonl_dataset(
    path: Path,
) -> list[EvaluationCaseDefinition]:
    return load_jsonl_text(
        path.read_text(encoding="utf-8"),
        source=str(path),
    )


def load_jsonl_text(
    content: str,
    *,
    source: str = "<evaluation-dataset>",
) -> list[EvaluationCaseDefinition]:
    cases: list[EvaluationCaseDefinition] = []
    external_ids: set[str] = set()

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()

        if not stripped:
            continue

        try:
            raw = json.loads(stripped)
            case = EvaluationCaseDefinition.model_validate(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise DatasetLoadError(
                f"Invalid evaluation case at {source}:{line_number}"
            ) from exc

        if case.external_id in external_ids:
            raise DatasetLoadError(
                f"Duplicate external_id: {case.external_id}"
            )

        external_ids.add(case.external_id)
        cases.append(case)

    if not cases:
        raise DatasetLoadError(f"Dataset contains no cases: {source}")

    return cases
