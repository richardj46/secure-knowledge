from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from secure_knowledge_core.auth.exceptions import InvalidTokenError
from secure_knowledge_core.auth.schemas import TokenPayload
from secure_knowledge_core.core.settings import get_settings


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()

    now = datetime.now(UTC)
    expires_at = now + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "token_type": "access",
        "iat": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> TokenPayload:
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "require": [
                    "sub",
                    "exp",
                    "iat",
                    "iss",
                    "aud",
                    "token_type",
                ]
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Access token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Access token is invalid.") from exc

    if payload.get("token_type") != "access":
        raise InvalidTokenError("Unexpected token type.")

    try:
        return TokenPayload(
            sub=UUID(payload["sub"]),
            token_type=payload["token_type"],
            iss=payload["iss"],
            aud=payload["aud"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenError("Access token payload is invalid.") from exc
