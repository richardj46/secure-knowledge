from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class ClaimCitationPair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    cited_passages: list[str]


class CitationCorrectnessGrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supported: bool
    score: float = Field(ge=0.0, le=1.0)
    explanation: str


class ClaimCitationGrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_index: int = Field(ge=1)
    claim: str
    grade: CitationCorrectnessGrade


class CitationCorrectnessResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_correctness: float = Field(ge=0.0, le=1.0)
    claim_grades: list[ClaimCitationGrade]


class CitationCorrectnessGraderProvider(Protocol):
    def grade_citation(
        self,
        *,
        pair: ClaimCitationPair,
    ) -> CitationCorrectnessGrade:
        ...


def grade_citation_correctness(
    *,
    provider: CitationCorrectnessGraderProvider,
    pairs: list[ClaimCitationPair],
) -> CitationCorrectnessResult:
    claim_grades = [
        ClaimCitationGrade(
            claim_index=index,
            claim=pair.claim,
            grade=provider.grade_citation(pair=pair),
        )
        for index, pair in enumerate(pairs, start=1)
    ]
    supported_count = sum(item.grade.supported for item in claim_grades)
    correctness = supported_count / len(claim_grades) if claim_grades else 1.0

    return CitationCorrectnessResult(
        citation_correctness=correctness,
        claim_grades=claim_grades,
    )
