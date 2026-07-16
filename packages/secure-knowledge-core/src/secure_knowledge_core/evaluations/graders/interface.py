from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class GraderResult:
    grader_name: str
    grader_version: str
    score: float
    passed: bool
    explanation: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


EvaluationGrade = GraderResult


class EvaluationGrader(Protocol):
    def grade(self, *, case: dict[str, Any], result: dict[str, Any]) -> GraderResult:
        ...
