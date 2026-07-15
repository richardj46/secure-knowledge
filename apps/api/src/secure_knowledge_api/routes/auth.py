from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from secure_knowledge_core.auth.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)
from secure_knowledge_core.auth.schemas import (
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from secure_knowledge_core.auth.service import AuthService
from secure_knowledge_core.auth.tokens import create_access_token
from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    session: DatabaseSession,
) -> UserRead:
    service = AuthService(session)

    try:
        user = service.register(data)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc

    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: DatabaseSession,
) -> TokenResponse:
    service = AuthService(session)

    try:
        user = service.authenticate(
            email=form_data.username,
            password=form_data.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(
        access_token=create_access_token(user.id),
    )


@router.get(
    "/me",
    response_model=UserRead,
)
def get_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)