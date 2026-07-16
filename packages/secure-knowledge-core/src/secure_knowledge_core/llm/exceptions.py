class AnswerProviderError(Exception):
    """The configured provider could not generate a usable answer."""


class AnswerProviderConfigurationError(AnswerProviderError):
    """The answer provider is not configured."""


class InvalidGeneratedAnswerError(AnswerProviderError):
    """The provider returned an invalid or unsafe structured answer."""


class CitationValidationError(Exception):
    """A generated answer contains invalid citation metadata."""
