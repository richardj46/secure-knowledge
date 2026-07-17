from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from secure_knowledge_core.admin.pagination import (
    Page,
    decode_datetime_cursor,
    encode_datetime_cursor,
)
from secure_knowledge_core.audit.events import AuditEventType
from secure_knowledge_core.audit.service import AuditService
from secure_knowledge_core.authorization.service import AuthorizationService
from secure_knowledge_core.database.enums import (
    EvaluationCaseStatus,
    EvaluationRunStatus,
    HumanReviewStatus,
    ReviewStatus,
)
from secure_knowledge_core.database.models import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationCaseReview,
    EvaluationDataset,
    EvaluationGraderResult,
    EvaluationMetricResult,
    EvaluationRun,
)
from secure_knowledge_core.evaluations.schemas import EvaluationCaseReviewRead
from secure_knowledge_core.evaluations.service import EvaluationService


class AdminEvaluationResourceNotFoundError(Exception):
    """Raised when an evaluation resource is outside the admin's scope."""


class RegressionClassification(StrEnum):
    NONE = "none"
    SECURITY = "security"
    QUALITY = "quality"
    SECURITY_AND_QUALITY = "security_and_quality"


class BaselineDeltaRead(BaseModel):
    metric_name: str
    delta: float
    baseline_value: float | None
    current_value: float | None
    increase_ratio: float | None
    passed: bool | None
    threshold: float | None


class EvaluationRunAdminSummary(BaseModel):
    id: UUID
    dataset_id: UUID
    dataset: str
    dataset_version: int
    status: EvaluationRunStatus
    case_pass_rate: float | None
    authorization_leakage_rate: float | None
    document_recall_at_5: float | None
    groundedness: float | None
    unsafe_answer_rate: float | None
    p95_latency_ms: float | None
    average_cost_microusd: float | None
    baseline_run_id: UUID | None
    baseline_delta: list[BaselineDeltaRead]
    regression_classification: RegressionClassification
    security_regression: bool
    quality_regression: bool
    code_revision: str | None
    created_at: datetime


class EvaluationMetricAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metric_name: str
    metric_version: str
    value: float
    passed: bool | None
    threshold: float | None
    details: dict[str, Any]


class EvaluationRunAdminDetail(EvaluationRunAdminSummary):
    organization_id: UUID
    started_by_user_id: UUID
    configuration: dict[str, Any]
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
    started_at: datetime | None
    completed_at: datetime | None
    failure_message: str | None
    metrics: list[EvaluationMetricAdminRead]


class EvaluationCaseResultAdminSummary(BaseModel):
    id: UUID
    evaluation_case_id: UUID
    external_id: str
    name: str
    question: str
    expected_answerability: str | None
    actual_answerability: str | None
    status: EvaluationCaseStatus
    deterministic_passed: bool | None
    hard_gates_passed: bool | None
    hard_gate_violations: list[str]
    overall_score: float | None
    latency_ms: int | None
    estimated_cost_microusd: int | None
    human_review_status: HumanReviewStatus
    error_code: str | None
    created_at: datetime


class EvaluationGraderAdminRead(BaseModel):
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


class EvaluationCaseReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReviewStatus
    notes: str | None = Field(default=None, max_length=20_000)


class EvaluationCaseReviewAdminRead(BaseModel):
    id: UUID
    evaluation_case_result_id: UUID
    reviewer_user_id: UUID
    status: ReviewStatus
    notes: str | None
    created_at: datetime


class EvaluationCaseResultAdminDetail(EvaluationCaseResultAdminSummary):
    evaluation_run_id: UUID
    dataset_id: UUID
    dataset: str
    dataset_version: int
    definition: dict[str, Any]
    tags: list[str]
    retrieval_run_id: UUID | None
    answer_run_id: UUID | None
    actual_answer: str | None
    retrieved_document_ids: list[UUID]
    retrieved_chunk_ids: list[UUID]
    context_chunk_ids: list[UUID]
    error_message: str | None
    metrics: list[EvaluationMetricAdminRead]
    graders: list[EvaluationGraderAdminRead]
    review_evidence: EvaluationCaseReviewRead
    reviews: list[EvaluationCaseReviewAdminRead]


class AdminEvaluationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.authorization = AuthorizationService(session)
        self.audit = AuditService(session)

    def list_runs(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        limit: int,
        cursor: str | None,
    ) -> Page[EvaluationRunAdminSummary]:
        self._require_admin(organization_id, actor_user_id)
        statement = (
            select(EvaluationRun, EvaluationDataset)
            .join(
                EvaluationDataset,
                EvaluationDataset.id == EvaluationRun.dataset_id,
            )
            .where(
                EvaluationRun.organization_id == organization_id,
                EvaluationDataset.organization_id == organization_id,
            )
        )
        if cursor is not None:
            cursor_time, cursor_id = decode_datetime_cursor(cursor)
            statement = statement.where(
                or_(
                    EvaluationRun.created_at < cursor_time,
                    and_(
                        EvaluationRun.created_at == cursor_time,
                        EvaluationRun.id < cursor_id,
                    ),
                )
            )
        rows = self.session.execute(
            statement.order_by(
                EvaluationRun.created_at.desc(),
                EvaluationRun.id.desc(),
            ).limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        run_ids = [run.id for run, _ in rows]
        metrics_by_run = self._aggregate_metrics_by_run(run_ids)
        items = [
            self._run_summary(
                run=run,
                dataset=dataset,
                metrics=metrics_by_run.get(run.id, []),
            )
            for run, dataset in rows
        ]
        next_cursor = (
            encode_datetime_cursor(rows[-1][0].created_at, rows[-1][0].id)
            if has_more and rows
            else None
        )
        return Page(items=items, next_cursor=next_cursor)

    def get_run(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        run_id: UUID,
    ) -> EvaluationRunAdminDetail:
        self._require_admin(organization_id, actor_user_id)
        row = self._run_row(organization_id=organization_id, run_id=run_id)
        if row is None:
            raise AdminEvaluationResourceNotFoundError
        run, dataset = row
        metrics = self._aggregate_metrics_by_run([run.id]).get(run.id, [])
        summary = self._run_summary(
            run=run,
            dataset=dataset,
            metrics=metrics,
        )
        return EvaluationRunAdminDetail(
            **summary.model_dump(),
            organization_id=run.organization_id,
            started_by_user_id=run.started_by_user_id,
            configuration=dict(run.configuration),
            answer_prompt_version=run.answer_prompt_version,
            grader_prompt_version=run.grader_prompt_version,
            answer_model=run.answer_model,
            embedding_model=run.embedding_model,
            reranker_model=run.reranker_model,
            chunking_version=run.chunking_version,
            retrieval_configuration_version=run.retrieval_configuration_version,
            authorization_policy_version=run.authorization_policy_version,
            total_cases=run.total_cases,
            completed_cases=run.completed_cases,
            passed_cases=run.passed_cases,
            failed_cases=run.failed_cases,
            hard_gates_passed=run.hard_gates_passed,
            quality_gates_passed=run.quality_gates_passed,
            regression_passed=run.regression_passed,
            started_at=run.started_at,
            completed_at=run.completed_at,
            failure_message=run.failure_message,
            metrics=[
                EvaluationMetricAdminRead.model_validate(metric)
                for metric in metrics
            ],
        )

    def list_cases(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        run_id: UUID,
        limit: int,
        cursor: str | None,
    ) -> Page[EvaluationCaseResultAdminSummary]:
        self._require_admin(organization_id, actor_user_id)
        if self._run_row(organization_id=organization_id, run_id=run_id) is None:
            raise AdminEvaluationResourceNotFoundError
        conditions = (
            EvaluationCaseResult.evaluation_run_id == run_id,
            EvaluationCase.organization_id == organization_id,
        )
        statement = (
            select(EvaluationCaseResult, EvaluationCase)
            .join(
                EvaluationCase,
                EvaluationCase.id == EvaluationCaseResult.evaluation_case_id,
            )
            .where(*conditions)
        )
        if cursor is not None:
            cursor_time, cursor_id = decode_datetime_cursor(cursor)
            statement = statement.where(
                or_(
                    EvaluationCaseResult.created_at > cursor_time,
                    and_(
                        EvaluationCaseResult.created_at == cursor_time,
                        EvaluationCaseResult.id > cursor_id,
                    ),
                )
            )
        rows = self.session.execute(
            statement.order_by(
                EvaluationCaseResult.created_at,
                EvaluationCaseResult.id,
            )
            .limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [self._case_summary(result, case) for result, case in rows]
        next_cursor = (
            encode_datetime_cursor(rows[-1][0].created_at, rows[-1][0].id)
            if has_more and rows
            else None
        )
        return Page(items=items, next_cursor=next_cursor)

    def get_case_result(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        result_id: UUID,
    ) -> EvaluationCaseResultAdminDetail:
        self._require_admin(organization_id, actor_user_id)
        row = self._case_row(
            organization_id=organization_id,
            result_id=result_id,
        )
        if row is None:
            raise AdminEvaluationResourceNotFoundError
        result, case, run, dataset = row
        metrics = list(
            self.session.scalars(
                select(EvaluationMetricResult)
                .where(
                    EvaluationMetricResult.evaluation_case_result_id
                    == result.id
                )
                .order_by(EvaluationMetricResult.metric_name)
            )
        )
        graders = list(
            self.session.scalars(
                select(EvaluationGraderResult)
                .where(
                    EvaluationGraderResult.evaluation_case_result_id
                    == result.id
                )
                .order_by(
                    EvaluationGraderResult.grader_name,
                    EvaluationGraderResult.claim_index,
                    EvaluationGraderResult.id,
                )
            )
        )
        reviews = list(
            self.session.scalars(
                select(EvaluationCaseReview)
                .where(
                    EvaluationCaseReview.evaluation_case_result_id == result.id
                )
                .order_by(
                    EvaluationCaseReview.created_at,
                    EvaluationCaseReview.id,
                )
            )
        )
        evidence = EvaluationService(session=self.session).get_case_review(
            evaluation_case_result_id=result.id,
            user_id=actor_user_id,
        )
        return EvaluationCaseResultAdminDetail(
            **self._case_summary(result, case).model_dump(),
            evaluation_run_id=result.evaluation_run_id,
            dataset_id=dataset.id,
            dataset=dataset.name,
            dataset_version=dataset.version,
            definition=dict(case.definition),
            tags=list(case.tags),
            retrieval_run_id=result.retrieval_run_id,
            answer_run_id=result.answer_run_id,
            actual_answer=result.actual_answer,
            retrieved_document_ids=self._uuid_list(result.retrieved_document_ids),
            retrieved_chunk_ids=self._uuid_list(result.retrieved_chunk_ids),
            context_chunk_ids=self._uuid_list(result.context_chunk_ids),
            error_message=result.error_message,
            metrics=[
                EvaluationMetricAdminRead.model_validate(metric)
                for metric in metrics
            ],
            graders=[
                EvaluationGraderAdminRead.model_validate(grader)
                for grader in graders
            ],
            review_evidence=evidence,
            reviews=[self._review_read(review) for review in reviews],
        )

    def create_case_review(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        result_id: UUID,
        data: EvaluationCaseReviewCreate,
        request_id: str | None,
    ) -> EvaluationCaseReviewAdminRead:
        self._require_admin(organization_id, actor_user_id)
        row = self._case_row(
            organization_id=organization_id,
            result_id=result_id,
        )
        if row is None:
            raise AdminEvaluationResourceNotFoundError
        result, _, _, _ = row
        review = EvaluationCaseReview(
            evaluation_case_result_id=result.id,
            reviewer_user_id=actor_user_id,
            status=data.status,
            notes=data.notes,
        )
        self.session.add(review)
        result.human_review_status = HumanReviewStatus(data.status.value)
        result.human_notes = data.notes
        if data.status == ReviewStatus.PENDING:
            result.reviewed_by_user_id = None
            result.reviewed_at = None
        else:
            result.reviewed_by_user_id = actor_user_id
            result.reviewed_at = datetime.now(UTC)
        self.session.flush()
        self.audit.record(
            organization_id=organization_id,
            event_type=AuditEventType.ADMIN_EVALUATION_CASE_REVIEWED,
            resource_type="evaluation_case_result",
            resource_id=result.id,
            actor_user_id=actor_user_id,
            outcome="succeeded",
            request_id=request_id,
            details={
                "evaluation_case_review_id": str(review.id),
                "review_status": review.status.value,
            },
        )
        return self._review_read(review)

    def _run_row(
        self,
        *,
        organization_id: UUID,
        run_id: UUID,
    ) -> tuple[EvaluationRun, EvaluationDataset] | None:
        return self.session.execute(
            select(EvaluationRun, EvaluationDataset)
            .join(
                EvaluationDataset,
                EvaluationDataset.id == EvaluationRun.dataset_id,
            )
            .where(
                EvaluationRun.id == run_id,
                EvaluationRun.organization_id == organization_id,
                EvaluationDataset.organization_id == organization_id,
            )
        ).one_or_none()

    def _case_row(
        self,
        *,
        organization_id: UUID,
        result_id: UUID,
    ) -> tuple[
        EvaluationCaseResult,
        EvaluationCase,
        EvaluationRun,
        EvaluationDataset,
    ] | None:
        return self.session.execute(
            select(
                EvaluationCaseResult,
                EvaluationCase,
                EvaluationRun,
                EvaluationDataset,
            )
            .join(
                EvaluationCase,
                EvaluationCase.id == EvaluationCaseResult.evaluation_case_id,
            )
            .join(
                EvaluationRun,
                EvaluationRun.id == EvaluationCaseResult.evaluation_run_id,
            )
            .join(
                EvaluationDataset,
                EvaluationDataset.id == EvaluationRun.dataset_id,
            )
            .where(
                EvaluationCaseResult.id == result_id,
                EvaluationRun.organization_id == organization_id,
                EvaluationCase.organization_id == organization_id,
                EvaluationDataset.organization_id == organization_id,
            )
        ).one_or_none()

    def _aggregate_metrics_by_run(
        self,
        run_ids: list[UUID],
    ) -> dict[UUID, list[EvaluationMetricResult]]:
        if not run_ids:
            return {}
        rows = self.session.scalars(
            select(EvaluationMetricResult)
            .where(
                EvaluationMetricResult.evaluation_run_id.in_(run_ids),
                EvaluationMetricResult.evaluation_case_result_id.is_(None),
            )
            .order_by(
                EvaluationMetricResult.evaluation_run_id,
                EvaluationMetricResult.metric_name,
            )
        )
        grouped: dict[UUID, list[EvaluationMetricResult]] = {}
        for metric in rows:
            grouped.setdefault(metric.evaluation_run_id, []).append(metric)
        return grouped

    def _run_summary(
        self,
        *,
        run: EvaluationRun,
        dataset: EvaluationDataset,
        metrics: list[EvaluationMetricResult],
    ) -> EvaluationRunAdminSummary:
        values = {
            metric.metric_name: metric.value
            for metric in metrics
            if not metric.metric_name.startswith("baseline_delta.")
        }
        baseline_delta = [
            self._baseline_delta(metric)
            for metric in metrics
            if metric.metric_name.startswith("baseline_delta.")
        ]
        security_regression = (
            run.hard_gates_passed is False
            or values.get("authorization_leakage_rate", 0.0) > 0.0
        )
        quality_regression = (
            run.quality_gates_passed is False
            or (
                run.regression_passed is False
                and not security_regression
            )
        )
        return EvaluationRunAdminSummary(
            id=run.id,
            dataset_id=dataset.id,
            dataset=dataset.name,
            dataset_version=dataset.version,
            status=run.status,
            case_pass_rate=values.get("case_pass_rate"),
            authorization_leakage_rate=values.get(
                "authorization_leakage_rate"
            ),
            document_recall_at_5=values.get("document_recall@5"),
            groundedness=values.get("groundedness"),
            unsafe_answer_rate=values.get("unsafe_answer_rate"),
            p95_latency_ms=values.get("p95_latency"),
            average_cost_microusd=values.get("average_cost"),
            baseline_run_id=run.baseline_run_id,
            baseline_delta=baseline_delta,
            regression_classification=self._regression_classification(
                security_regression=security_regression,
                quality_regression=quality_regression,
            ),
            security_regression=security_regression,
            quality_regression=quality_regression,
            code_revision=run.code_revision,
            created_at=run.created_at,
        )

    @staticmethod
    def _baseline_delta(metric: EvaluationMetricResult) -> BaselineDeltaRead:
        details = metric.details
        return BaselineDeltaRead(
            metric_name=metric.metric_name.removeprefix("baseline_delta."),
            delta=metric.value,
            baseline_value=AdminEvaluationService._optional_float(
                details.get("baseline_value")
            ),
            current_value=AdminEvaluationService._optional_float(
                details.get("current_value")
            ),
            increase_ratio=AdminEvaluationService._optional_float(
                details.get("increase_ratio")
            ),
            passed=metric.passed,
            threshold=metric.threshold,
        )

    @staticmethod
    def _case_summary(
        result: EvaluationCaseResult,
        case: EvaluationCase,
    ) -> EvaluationCaseResultAdminSummary:
        expected = case.definition.get("expected_answerability")
        return EvaluationCaseResultAdminSummary(
            id=result.id,
            evaluation_case_id=case.id,
            external_id=case.external_id,
            name=case.name,
            question=case.question,
            expected_answerability=(str(expected) if expected is not None else None),
            actual_answerability=result.actual_answerability,
            status=result.status,
            deterministic_passed=result.deterministic_passed,
            hard_gates_passed=result.hard_gates_passed,
            hard_gate_violations=list(result.hard_gate_violations),
            overall_score=result.overall_score,
            latency_ms=result.latency_ms,
            estimated_cost_microusd=result.estimated_cost_microusd,
            human_review_status=result.human_review_status,
            error_code=result.error_code,
            created_at=result.created_at,
        )

    @staticmethod
    def _review_read(
        review: EvaluationCaseReview,
    ) -> EvaluationCaseReviewAdminRead:
        return EvaluationCaseReviewAdminRead(
            id=review.id,
            evaluation_case_result_id=review.evaluation_case_result_id,
            reviewer_user_id=review.reviewer_user_id,
            status=review.status,
            notes=review.notes,
            created_at=review.created_at,
        )

    @staticmethod
    def _uuid_list(values: list[str]) -> list[UUID]:
        return [UUID(str(value)) for value in values]

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _regression_classification(
        *,
        security_regression: bool,
        quality_regression: bool,
    ) -> RegressionClassification:
        if security_regression and quality_regression:
            return RegressionClassification.SECURITY_AND_QUALITY
        if security_regression:
            return RegressionClassification.SECURITY
        if quality_regression:
            return RegressionClassification.QUALITY
        return RegressionClassification.NONE

    def _require_admin(
        self,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        self.authorization.require_admin_access(
            organization_id=organization_id,
            user_id=actor_user_id,
        )
