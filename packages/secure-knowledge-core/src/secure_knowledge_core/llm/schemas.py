from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from secure_knowledge_core.database.enums import Answerability


class StrictAnswerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CitationDraft(StrictAnswerModel):
    chunk_id: UUID
    claims: list[str] = Field(min_length=1)


class GeneratedAnswer(StrictAnswerModel):
    answer: str
    answerability: Answerability
    confidence: float = Field(ge=0, le=1)
    citations: list[CitationDraft]
    limitations: list[str] = Field(default_factory=list)
