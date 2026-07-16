from uuid import UUID

from pydantic import BaseModel, Field


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    workspace_ids: list[UUID] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=50)


class RetrievalResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    page_number: int | None
    section_title: str | None
    score: float
    vector_rank: int | None
    keyword_rank: int | None
    vector_score: float | None = Field(default=None, exclude=True)
    keyword_score: float | None = Field(default=None, exclude=True)
    retrieval_sources: list[str]


class RetrievalSearchResponse(BaseModel):
    retrieval_run_id: UUID
    query: str
    results: list[RetrievalResult]
