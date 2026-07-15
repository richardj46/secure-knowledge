from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from secure_knowledge_core.database.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.session.scalar(statement)

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def add(self, user: User) -> None:
        self.session.add(user)