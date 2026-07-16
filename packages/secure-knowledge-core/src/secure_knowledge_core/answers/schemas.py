from uuid import UUID

from pydantic import BaseModel, Field

from secure_knowledge_core.database.enums import Answerability


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    workspace_ids: list[UUID] = Field(default_factory=list)


class AnswerCitationResponse(BaseModel):
    document_id: UUID
    document_title: str
    chunk_id: UUID
    page_number: int | None


class AnswerResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    answerability: Answerability
    confidence: float
    citations: list[AnswerCitationResponse]
    limitations: list[str]
