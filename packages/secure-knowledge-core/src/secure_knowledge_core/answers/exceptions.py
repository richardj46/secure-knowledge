class AnswerError(Exception):
    """Base answer-generation error."""


class CitationValidationError(AnswerError):
    pass


class ConversationAccessDeniedError(AnswerError):
    pass


class AnswerGenerationFailedError(AnswerError):
    pass


class RetrievalTraceMissingError(AnswerError):
    """Secure retrieval completed without creating its durable trace."""
