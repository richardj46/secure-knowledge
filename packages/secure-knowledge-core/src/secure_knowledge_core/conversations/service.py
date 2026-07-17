from uuid import UUID

from sqlalchemy.orm import Session

from secure_knowledge_core.conversations.exceptions import ConversationNotFoundError
from secure_knowledge_core.conversations.repository import ConversationRepository
from secure_knowledge_core.database.models import Conversation


class ConversationService:
    def __init__(
        self,
        session: Session,
        *,
        repository: ConversationRepository | None = None,
    ) -> None:
        self.repository = repository or ConversationRepository(session)

    def get_or_create(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        conversation_id: UUID | None,
        first_message: str,
    ) -> Conversation:
        if conversation_id is None:
            return self.repository.add(
                Conversation(
                    organization_id=organization_id,
                    user_id=user_id,
                    title=first_message.strip()[:300],
                )
            )

        conversation = self.repository.get_owned(
            conversation_id=conversation_id,
            organization_id=organization_id,
            user_id=user_id,
        )
        if conversation is None:
            raise ConversationNotFoundError
        return conversation
