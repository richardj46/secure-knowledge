class ConversationNotFoundError(Exception):
    """The conversation is unavailable to the requesting user."""


class RetrievalTraceMissingError(Exception):
    """Secure retrieval completed without creating its durable trace."""
