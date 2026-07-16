from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from secure_knowledge_core.database.models import Conversation


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, conversation: Conversation) -> Conversation:
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def add_conversation(self, conversation: Conversation) -> None:
        self.session.add(conversation)

    def get_owned(
        self,
        *,
        conversation_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> Conversation | None:
        return self.session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.organization_id == organization_id,
                Conversation.user_id == user_id,
            )
        )

    def get_for_user(
        self,
        *,
        conversation_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> Conversation | None:
        return self.get_owned(
            conversation_id=conversation_id,
            organization_id=organization_id,
            user_id=user_id,
        )
