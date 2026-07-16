from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExpectedAnswerability(StrEnum):
    ANSWERABLE = "answerable"
    PARTIALLY_ANSWERABLE = "partially_answerable"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"


class EvaluationCaseDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=300)

    user_id: UUID
    organization_id: UUID
    workspace_ids: list[UUID] = Field(default_factory=list)

    question: str = Field(min_length=1, max_length=4000)

    expected_answerability: ExpectedAnswerability

    expected_document_ids: list[UUID] = Field(default_factory=list)
    expected_chunk_ids: list[UUID] = Field(default_factory=list)
    expected_citation_count: int | None = Field(
        default=None,
        ge=0,
        le=20,
    )
    authorized_evidence_texts: list[str] = Field(default_factory=list)

    forbidden_document_ids: list[UUID] = Field(default_factory=list)
    forbidden_chunk_ids: list[UUID] = Field(default_factory=list)
    forbidden_organization_ids: list[UUID] = Field(default_factory=list)
    forbidden_evidence_texts: list[str] = Field(default_factory=list)

    reference_answer: str | None = None
    required_claims: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)

    tags: list[str] = Field(default_factory=list)
