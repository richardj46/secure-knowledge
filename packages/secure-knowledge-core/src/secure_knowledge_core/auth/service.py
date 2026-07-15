from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from secure_knowledge_core.auth.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)
from secure_knowledge_core.auth.password import hash_password, verify_password
from secure_knowledge_core.auth.repository import UserRepository
from secure_knowledge_core.auth.schemas import RegisterRequest
from secure_knowledge_core.database.models import User


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def register(self, data: RegisterRequest) -> User:
        normalized_email = data.email.strip().lower()

        existing_user = self.users.get_by_email(normalized_email)
        if existing_user is not None:
            raise EmailAlreadyRegisteredError

        user = User(
            email=normalized_email,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
        )

        try:
            self.users.add(user)
            self.session.flush()
        except IntegrityError as exc:
            # The database unique constraint remains the final protection
            # against two simultaneous registrations with the same email.
            raise EmailAlreadyRegisteredError from exc

        return user

    def authenticate(
        self,
        *,
        email: str,
        password: str,
    ) -> User:
        normalized_email = email.strip().lower()
        user = self.users.get_by_email(normalized_email)

        if user is None:
            raise InvalidCredentialsError

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError

        return user
