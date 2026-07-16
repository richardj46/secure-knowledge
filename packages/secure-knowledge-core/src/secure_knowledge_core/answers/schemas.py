from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from secure_knowledge_core.database.enums import Answerability


class StrictAnswerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    workspace_ids: list[UUID] = Field(default_factory=list)


class CitationDraft(StrictAnswerModel):
    chunk_id: UUID
    claims: list[str] = Field(min_length=1, max_length=10)


class GeneratedAnswer(StrictAnswerModel):
    answer: str = Field(max_length=20_000)
    answerability: Answerability
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[CitationDraft] = Field(
        default_factory=list,
        max_length=20,
    )
    limitations: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

    @model_validator(mode="after")
    def validate_answer_shape(self) -> Self:
        if self.answerability == Answerability.ANSWERABLE:
            if not self.answer.strip():
                raise ValueError(
                    "An answerable result must include an answer."
                )

            if not self.citations:
                raise ValueError(
                    "An answerable result must include citations."
                )

        if self.answerability == Answerability.NOT_FOUND:
            if self.citations:
                raise ValueError(
                    "A not-found result must not contain citations."
                )

        return self


class AnswerCitationRead(BaseModel):
    document_id: UUID
    document_title: str
    chunk_id: UUID
    page_number: int | None
    claims: list[str]


AnswerCitationResponse = AnswerCitationRead


class AnswerResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    answer_run_id: UUID
    answer: str
    answerability: Answerability
    confidence: float
    citations: list[AnswerCitationRead]
    limitations: list[str]
