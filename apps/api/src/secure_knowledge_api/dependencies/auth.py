from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.auth.exceptions import InvalidTokenError
from secure_knowledge_core.auth.repository import UserRepository
from secure_knowledge_core.auth.tokens import decode_access_token
from secure_knowledge_core.database.models import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)

BearerToken = Annotated[str, Depends(oauth2_scheme)]


def get_current_user(
    token: BearerToken,
    session: DatabaseSession,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_payload = decode_access_token(token)
    except InvalidTokenError as exc:
        raise credentials_exception from exc

    user = UserRepository(session).get_by_id(token_payload.sub)

    if user is None:
        raise credentials_exception

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
