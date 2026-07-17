from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from secure_knowledge_core.database.enums import (
    Answerability,
    EvaluationCaseStatus,
    EvaluationRunStatus,
    HumanReviewStatus,
)
from secure_knowledge_core.evaluations.metrics.regression import RegressionLimits
from secure_knowledge_core.evaluations.modes import (
    EvaluationRunMode,
    get_mode_policy,
)


class EvaluationDatasetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    version: int = Field(default=1, ge=1)


class EvaluationDatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    version: int
    is_active: bool


class EvaluationCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    external_id: str
    name: str
    user_id: UUID
    organization_id: UUID
    question: str
    definition: dict[str, Any]
    tags: list[str]


class EvaluationCaseImportRead(BaseModel):
    imported_count: int


class EvaluationRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: EvaluationRunMode = EvaluationRunMode.DETERMINISTIC
    code_revision: str | None = Field(default=None, max_length=100)
    baseline_run_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)

    include_answer_generation: bool = True
    include_model_graders: bool = False

    retrieval_limit: int = Field(default=10, ge=1, le=50)

    answer_model: str | None = None
    grader_model: str | None = None
    regression_limits: RegressionLimits = Field(
        default_factory=RegressionLimits,
    )

    @model_validator(mode="after")
    def validate_mode_configuration(self) -> EvaluationRunCreate:
        if self.mode == EvaluationRunMode.DETERMINISTIC:
            if self.include_model_graders:
                raise ValueError(
                    "Deterministic runs cannot use model graders."
                )
            if self.answer_model is not None or self.grader_model is not None:
                raise ValueError(
                    "Deterministic runs cannot select external models."
                )

        if self.include_model_graders and not self.include_answer_generation:
            raise ValueError(
                "Model graders require answer generation."
            )
        if not self.include_answer_generation and self.answer_model is not None:
            raise ValueError(
                "An answer model requires answer generation."
            )
        if not self.include_model_graders and self.grader_model is not None:
            raise ValueError(
                "A grader model requires model graders."
            )
        return self

    def build_configuration(
        self,
        *,
        default_answer_model: str,
        default_embedding_model: str,
    ) -> dict[str, Any]:
        configuration = self.model_dump(
            mode="json",
            exclude={"baseline_run_id", "code_revision"},
        )
        policy = get_mode_policy(self.mode)

        if self.mode == EvaluationRunMode.DETERMINISTIC:
            configuration["embedding_model"] = "fixed"
            configuration["answer_model"] = (
                "fake-answer-model"
                if self.include_answer_generation
                else None
            )
        else:
            configuration["embedding_model"] = default_embedding_model
            configuration["answer_model"] = (
                self.answer_model or default_answer_model
                if self.include_answer_generation
                else None
            )

        configuration["grader_model"] = (
            self.grader_model or configuration["answer_model"]
            if self.include_model_graders
            else None
        )
        mode_policy = policy.as_configuration()
        if not self.include_answer_generation:
            mode_policy["answer_provider"] = "disabled"
        if not self.include_model_graders:
            mode_policy["model_grader_provider"] = "disabled"
        configuration["mode_policy"] = mode_policy
        return configuration


class EvaluationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    organization_id: UUID
    started_by_user_id: UUID
    baseline_run_id: UUID | None
    status: EvaluationRunStatus
    configuration: dict[str, Any]
    code_revision: str | None
    answer_prompt_version: str
    grader_prompt_version: str
    answer_model: str | None
    embedding_model: str
    reranker_model: str | None
    chunking_version: str
    retrieval_configuration_version: str
    authorization_policy_version: str
    total_cases: int
    completed_cases: int
    passed_cases: int
    failed_cases: int
    hard_gates_passed: bool | None
    quality_gates_passed: bool | None
    regression_passed: bool | None
    failure_message: str | None


class EvaluationCaseResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evaluation_run_id: UUID
    evaluation_case_id: UUID
    status: EvaluationCaseStatus
    retrieval_run_id: UUID | None
    answer_run_id: UUID | None
    actual_answerability: str | None
    actual_answer: str | None
    retrieved_document_ids: list[str]
    retrieved_chunk_ids: list[str]
    context_chunk_ids: list[str]
    latency_ms: int | None
    estimated_cost_microusd: int | None
    deterministic_passed: bool | None
    hard_gates_passed: bool | None
    hard_gate_violations: list[str]
    overall_score: float | None
    error_code: str | None
    error_message: str | None
    human_review_status: HumanReviewStatus
    human_score: float | None
    human_notes: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None


class EvaluationMetricResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evaluation_run_id: UUID
    evaluation_case_result_id: UUID | None
    metric_name: str
    metric_version: str
    value: float
    passed: bool | None
    threshold: float | None
    details: dict[str, Any]


class HumanReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: HumanReviewStatus
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = Field(default=None, max_length=20_000)


class EvaluationReviewPassage(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    page_number: int | None
    section_title: str | None


class EvaluationReviewCitation(BaseModel):
    citation_index: int
    chunk_id: UUID
    document_id: UUID
    document_title: str
    page_number: int | None
    claims: list[str]


class EvaluationGraderResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    grader_name: str
    grader_version: str
    claim_index: int | None
    claim: str | None
    score: float
    passed: bool
    explanation: str | None
    details: dict[str, Any]


class EvaluationCaseReviewRead(BaseModel):
    evaluation_case_result_id: UUID
    evaluation_run_id: UUID
    question: str
    expected_answerability: str
    retrieved_chunk_ids: list[UUID]
    selected_context_chunk_ids: list[UUID]
    retrieved_passages: list[EvaluationReviewPassage]
    selected_context: list[EvaluationReviewPassage]
    generated_answer: str | None
    citations: list[EvaluationReviewCitation]
    deterministic_metrics: list[EvaluationMetricResultRead]
    model_grades: list[EvaluationGraderResultRead]
    human_review_status: HumanReviewStatus
    human_score: float | None
    human_notes: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None


@dataclass(frozen=True)
class EvaluationExecution:
    retrieval_run_id: UUID
    answer_run_id: UUID | None

    vector_candidate_chunk_ids: list[UUID]
    keyword_candidate_chunk_ids: list[UUID]
    fused_chunk_ids: list[UUID]
    selected_context_chunk_ids: list[UUID]

    retrieved_document_ids: list[UUID]
    retrieved_chunk_ids: list[UUID]
    cited_chunk_ids: list[UUID]

    actual_answerability: Answerability
    answer: str

    retrieval_latency_ms: int
    generation_latency_ms: int
    total_latency_ms: int

    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_microusd: int | None
