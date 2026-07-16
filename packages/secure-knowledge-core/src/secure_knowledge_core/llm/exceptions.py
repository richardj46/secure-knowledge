from secure_knowledge_core.answers.exceptions import CitationValidationError


class AnswerProviderError(Exception):
    """The configured provider could not generate a usable answer."""


class AnswerProviderConfigurationError(AnswerProviderError):
    """The answer provider is not configured."""


class InvalidGeneratedAnswerError(AnswerProviderError):
    """The provider returned an invalid or unsafe structured answer."""


__all__ = [
    "AnswerProviderConfigurationError",
    "AnswerProviderError",
    "CitationValidationError",
    "InvalidGeneratedAnswerError",
]
