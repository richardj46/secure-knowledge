"""Deterministic graders composed from the evaluation metric functions."""

from secure_knowledge_core.evaluations.graders.interface import GraderResult
from secure_knowledge_core.evaluations.metrics import (
    score_abstention_quality,
    score_answer_quality,
    score_authorization_safety,
    score_retrieval_quality,
)


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def grade_forbidden_claims(
    *,
    answer: str,
    forbidden_claims: list[str],
) -> GraderResult:
    """Fail when the answer contains any normalized forbidden claim."""
    normalized_answer = normalize_text(answer)

    matched = [
        claim
        for claim in forbidden_claims
        if normalize_text(claim) in normalized_answer
    ]

    return GraderResult(
        grader_name="forbidden-claims",
        grader_version="v1",
        score=1.0 if not matched else 0.0,
        passed=not matched,
        explanation=None,
        details={"matched_forbidden_claims": matched},
    )


def grade_required_claims(
    *,
    answer: str,
    required_claims: list[str],
) -> GraderResult:
    """Grade literal required claims after whitespace and case normalization."""
    normalized_answer = normalize_text(answer)

    missing = [
        claim
        for claim in required_claims
        if normalize_text(claim) not in normalized_answer
    ]

    score = (
        1.0
        if not required_claims
        else (len(required_claims) - len(missing)) / len(required_claims)
    )

    return GraderResult(
        grader_name="required-claims",
        grader_version="v1",
        score=score,
        passed=not missing,
        explanation=None,
        details={"missing_claims": missing},
    )


__all__ = [
    "grade_forbidden_claims",
    "grade_required_claims",
    "normalize_text",
    "score_abstention_quality",
    "score_answer_quality",
    "score_authorization_safety",
    "score_retrieval_quality",
]
