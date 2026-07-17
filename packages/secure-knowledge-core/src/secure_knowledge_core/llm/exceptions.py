class LLMProviderError(Exception):
    """Base model-provider error."""


class LLMProviderConfigurationError(LLMProviderError):
    pass


class LLMProviderTimeoutError(LLMProviderError):
    pass


class LLMProviderRateLimitError(LLMProviderError):
    pass


class LLMProviderUnavailableError(LLMProviderError):
    pass


class LLMInvalidStructuredOutputError(LLMProviderError):
    pass


class LLMRefusalError(LLMProviderError):
    pass


__all__ = [
    "LLMInvalidStructuredOutputError",
    "LLMProviderConfigurationError",
    "LLMProviderError",
    "LLMProviderRateLimitError",
    "LLMProviderTimeoutError",
    "LLMProviderUnavailableError",
    "LLMRefusalError",
]
