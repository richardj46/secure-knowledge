class OrganizationNotFoundError(Exception):
    """The actor is not a member of the requested organization."""


class WorkspaceFilterNotFoundError(Exception):
    """At least one requested workspace is unavailable to the actor."""


class RetrievalUnavailableError(Exception):
    """Retrieval cannot currently generate or search query embeddings."""
