from sqlalchemy.exc import OperationalError

from secure_knowledge_core.ingestion.exceptions import TransientIngestionError
from secure_knowledge_core.llm.exceptions import (
    LLMInvalidStructuredOutputError,
    LLMProviderConfigurationError,
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMRefusalError,
)


class EvaluationError(Exception):
    """Base evaluation error."""


class EvaluationDatasetNotFoundError(EvaluationError):
    pass


class EvaluationAccessDeniedError(EvaluationError):
    pass


class EvaluationDatasetConflictError(EvaluationError):
    pass


class EvaluationDatasetReleasedError(EvaluationError):
    pass


class EvaluationCaseScopeError(EvaluationError):
    pass


class EvaluationRunNotFoundError(EvaluationError):
    pass


class EvaluationCaseResultNotFoundError(EvaluationError):
    pass


class EvaluationBaselineRunNotFoundError(EvaluationError):
    pass


class EvaluationBaselineRunNotReadyError(EvaluationError):
    pass


class EvaluationLiveDatasetTooLargeError(EvaluationError):
    pass


class EvaluationRunnerConfigurationError(EvaluationError):
    pass


class TransientEvaluationError(EvaluationError):
    """A retryable evaluation infrastructure failure."""


TRANSIENT_CAUSES = (
    LLMProviderRateLimitError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    OperationalError,
    TransientIngestionError,
)


def as_transient_evaluation_error(
    exception: BaseException,
) -> TransientEvaluationError | None:
    """Map only recognized infrastructure failures to a retryable error."""
    current: BaseException | None = exception
    visited: set[int] = set()

    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, TransientEvaluationError):
            return current
        if isinstance(current, TRANSIENT_CAUSES):
            return TransientEvaluationError(
                "Evaluation infrastructure is temporarily unavailable."
            )
        current = current.__cause__ or current.__context__

    return None


def evaluation_failure_code(exception: BaseException) -> str:
    current: BaseException | None = exception
    visited: set[int] = set()

    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, LLMProviderConfigurationError):
            return "provider_configuration_error"
        if isinstance(current, LLMInvalidStructuredOutputError):
            return "invalid_structured_output"
        if isinstance(current, LLMRefusalError):
            return "provider_refusal"
        if isinstance(current, LLMProviderError):
            return "provider_error"
        current = current.__cause__ or current.__context__

    return "evaluation_execution_error"
