class AuthenticationError(Exception):
    """Base authentication failure."""


class EmailAlreadyRegisteredError(AuthenticationError):
    """The requested email address already belongs to a user."""


class InvalidCredentialsError(AuthenticationError):
    """The supplied credentials are invalid."""


class InvalidTokenError(AuthenticationError):
    """The access token is invalid, malformed, or expired."""