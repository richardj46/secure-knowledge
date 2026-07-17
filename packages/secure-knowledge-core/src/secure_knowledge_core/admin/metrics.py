from datetime import UTC, datetime, timedelta
from statistics import fmean
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import String, cast, exists, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from secure_knowledge_core.authorization.service import AuthorizationService
from secure_knowledge_core.database.enums import (
    Answerability,
    AnswerGenerationStatus,
    DocumentStatus,
    ExecutionMode,
)
from secure_knowledge_core.database.models import (
    AnswerRun,
    Document,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationMetricResult,
    EvaluationRun,
    RetrievalResultRecord,
    RetrievalRun,
    Workspace,
)

DEFAULT_OVERVIEW_DAYS = 30
MAXIMUM_OVERVIEW_DAYS = 90


class AdminMetricsDateRangeError(Exception):
    """Raised when an overview range is invalid or too large."""


class AdminMetricsWorkspaceNotFoundError(Exception):
    """Raised when a workspace is outside the requested organization."""


class AdminOverviewMetrics(BaseModel):
    total_queries: int
    answered_queries: int
    abstained_queries: int
    failed_queries: int

    answer_rate: float
    abstention_rate: float
    failure_rate: float
    empty_retrieval_rate: float

    average_retrieval_latency_ms: float
    p95_retrieval_latency_ms: float
    average_generation_latency_ms: float
    p95_generation_latency_ms: float
    average_total_latency_ms: float
    p95_total_latency_ms: float

    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_microusd: int

    documents_ready: int
    documents_processing: int
    documents_failed: int

    evaluation_runs: int
    evaluation_pass_rate: float
    authorization_leakage_count: int


class AdminMetricsService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.authorization = AuthorizationService(session)

    def overview(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        date_from: datetime | None,
        date_to: datetime | None,
        workspace_id: UUID | None,
    ) -> AdminOverviewMetrics:
        self.authorization.require_admin_access(
            organization_id=organization_id,
            user_id=actor_user_id,
        )
        start, end = self._resolve_date_range(
            date_from=date_from,
            date_to=date_to,
        )
        if workspace_id is not None:
            self._require_workspace(
                organization_id=organization_id,
                workspace_id=workspace_id,
            )

        answer_rows = self._answer_rows(
            organization_id=organization_id,
            workspace_id=workspace_id,
            date_from=start,
            date_to=end,
        )
        total_queries = len(answer_rows)
        answered_queries = sum(
            run.status == AnswerGenerationStatus.COMPLETED
            and run.answerability
            in {
                Answerability.ANSWERABLE,
                Answerability.PARTIALLY_ANSWERABLE,
                Answerability.AMBIGUOUS,
            }
            for run, _ in answer_rows
        )
        abstained_queries = sum(
            run.status == AnswerGenerationStatus.COMPLETED
            and run.answerability == Answerability.NOT_FOUND
            for run, _ in answer_rows
        )
        failed_queries = sum(
            run.status == AnswerGenerationStatus.FAILED
            for run, _ in answer_rows
        )
        empty_retrievals = sum(
            retrieval.final_result_count == 0
            for _, retrieval in answer_rows
        )

        retrieval_latencies = [
            retrieval.duration_ms for _, retrieval in answer_rows
        ]
        generation_latencies = [
            run.generation_duration_ms
            for run, _ in answer_rows
            if run.generation_duration_ms is not None
        ]
        total_latencies = [
            retrieval.duration_ms + (run.generation_duration_ms or 0)
            for run, retrieval in answer_rows
        ]
        document_counts = self._document_counts(
            organization_id=organization_id,
            workspace_id=workspace_id,
        )
        evaluation_runs = self._evaluation_runs(
            organization_id=organization_id,
            workspace_id=workspace_id,
            date_from=start,
            date_to=end,
        )
        decided_evaluation_runs = [
            run for run in evaluation_runs if run.regression_passed is not None
        ]

        return AdminOverviewMetrics(
            total_queries=total_queries,
            answered_queries=answered_queries,
            abstained_queries=abstained_queries,
            failed_queries=failed_queries,
            answer_rate=self._ratio(answered_queries, total_queries),
            abstention_rate=self._ratio(abstained_queries, total_queries),
            failure_rate=self._ratio(failed_queries, total_queries),
            empty_retrieval_rate=self._ratio(
                empty_retrievals,
                total_queries,
            ),
            average_retrieval_latency_ms=self._average(retrieval_latencies),
            p95_retrieval_latency_ms=self._percentile(
                retrieval_latencies,
                0.95,
            ),
            average_generation_latency_ms=self._average(
                generation_latencies
            ),
            p95_generation_latency_ms=self._percentile(
                generation_latencies,
                0.95,
            ),
            average_total_latency_ms=self._average(total_latencies),
            p95_total_latency_ms=self._percentile(total_latencies, 0.95),
            total_input_tokens=sum(
                run.input_tokens or 0 for run, _ in answer_rows
            ),
            total_output_tokens=sum(
                run.output_tokens or 0 for run, _ in answer_rows
            ),
            total_estimated_cost_microusd=sum(
                run.estimated_cost_microusd or 0 for run, _ in answer_rows
            ),
            documents_ready=document_counts.get(DocumentStatus.READY, 0),
            documents_processing=sum(
                document_counts.get(status, 0)
                for status in self._processing_statuses()
            ),
            documents_failed=document_counts.get(DocumentStatus.FAILED, 0),
            evaluation_runs=len(evaluation_runs),
            evaluation_pass_rate=self._ratio(
                sum(run.regression_passed is True for run in decided_evaluation_runs),
                len(decided_evaluation_runs),
            ),
            authorization_leakage_count=self._authorization_leakage_count(
                organization_id=organization_id,
                workspace_id=workspace_id,
                date_from=start,
                date_to=end,
            ),
        )

    def _answer_rows(
        self,
        *,
        organization_id: UUID,
        workspace_id: UUID | None,
        date_from: datetime,
        date_to: datetime,
    ) -> list[tuple[AnswerRun, RetrievalRun]]:
        statement = (
            select(AnswerRun, RetrievalRun)
            .join(RetrievalRun, RetrievalRun.id == AnswerRun.retrieval_run_id)
            .where(
                AnswerRun.organization_id == organization_id,
                RetrievalRun.organization_id == organization_id,
                AnswerRun.execution_mode == ExecutionMode.PRODUCTION,
                RetrievalRun.execution_mode == ExecutionMode.PRODUCTION,
                AnswerRun.created_at >= date_from,
                AnswerRun.created_at <= date_to,
            )
        )
        if workspace_id is not None:
            statement = statement.where(
                self._retrieval_workspace_condition(workspace_id)
            )
        return [
            (answer_run, retrieval_run)
            for answer_run, retrieval_run in self.session.execute(statement)
        ]

    def _document_counts(
        self,
        *,
        organization_id: UUID,
        workspace_id: UUID | None,
    ) -> dict[DocumentStatus, int]:
        statement = (
            select(Document.status, func.count(Document.id))
            .where(
                Document.organization_id == organization_id,
                Document.status != DocumentStatus.DELETED,
            )
            .group_by(Document.status)
        )
        if workspace_id is not None:
            statement = statement.where(Document.workspace_id == workspace_id)
        return {
            status: int(count)
            for status, count in self.session.execute(statement).all()
        }

    def _evaluation_runs(
        self,
        *,
        organization_id: UUID,
        workspace_id: UUID | None,
        date_from: datetime,
        date_to: datetime,
    ) -> list[EvaluationRun]:
        statement = select(EvaluationRun).where(
            EvaluationRun.organization_id == organization_id,
            EvaluationRun.created_at >= date_from,
            EvaluationRun.created_at <= date_to,
        )
        if workspace_id is not None:
            statement = statement.where(
                exists(
                    select(1).where(
                        EvaluationCase.dataset_id == EvaluationRun.dataset_id,
                        cast(EvaluationCase.definition, String).contains(
                            str(workspace_id),
                            autoescape=True,
                        ),
                    )
                )
            )
        return list(self.session.scalars(statement))

    def _authorization_leakage_count(
        self,
        *,
        organization_id: UUID,
        workspace_id: UUID | None,
        date_from: datetime,
        date_to: datetime,
    ) -> int:
        statement = (
            select(func.count(EvaluationMetricResult.id))
            .join(
                EvaluationCaseResult,
                EvaluationCaseResult.id
                == EvaluationMetricResult.evaluation_case_result_id,
            )
            .join(
                EvaluationCase,
                EvaluationCase.id == EvaluationCaseResult.evaluation_case_id,
            )
            .join(
                EvaluationRun,
                EvaluationRun.id == EvaluationMetricResult.evaluation_run_id,
            )
            .where(
                EvaluationRun.organization_id == organization_id,
                EvaluationCase.organization_id == organization_id,
                EvaluationRun.created_at >= date_from,
                EvaluationRun.created_at <= date_to,
                EvaluationMetricResult.metric_name
                == "authorization_leakage_rate",
                EvaluationMetricResult.value > 0.0,
            )
        )
        if workspace_id is not None:
            statement = statement.where(
                cast(EvaluationCase.definition, String).contains(
                    str(workspace_id),
                    autoescape=True,
                )
            )
        return int(self.session.scalar(statement) or 0)

    def _require_workspace(
        self,
        *,
        organization_id: UUID,
        workspace_id: UUID,
    ) -> None:
        workspace_exists = self.session.scalar(
            select(Workspace.id).where(
                Workspace.id == workspace_id,
                Workspace.organization_id == organization_id,
            )
        )
        if workspace_exists is None:
            raise AdminMetricsWorkspaceNotFoundError

    @staticmethod
    def _retrieval_workspace_condition(
        workspace_id: UUID,
    ) -> ColumnElement[bool]:
        return or_(
            cast(RetrievalRun.workspace_ids, String).contains(
                str(workspace_id),
                autoescape=True,
            ),
            exists(
                select(1)
                .select_from(RetrievalResultRecord)
                .join(
                    Document,
                    Document.id == RetrievalResultRecord.document_id,
                )
                .where(
                    RetrievalResultRecord.retrieval_run_id == RetrievalRun.id,
                    Document.workspace_id == workspace_id,
                )
            ),
        )

    @staticmethod
    def _resolve_date_range(
        *,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> tuple[datetime, datetime]:
        end = AdminMetricsService._as_utc(date_to or datetime.now(UTC))
        start = AdminMetricsService._as_utc(
            date_from or end - timedelta(days=DEFAULT_OVERVIEW_DAYS)
        )
        if start > end:
            raise AdminMetricsDateRangeError(
                "date_from must be before or equal to date_to."
            )
        if end - start > timedelta(days=MAXIMUM_OVERVIEW_DAYS):
            raise AdminMetricsDateRangeError(
                f"The metrics range cannot exceed {MAXIMUM_OVERVIEW_DAYS} days."
            )
        return start, end

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _processing_statuses() -> tuple[DocumentStatus, ...]:
        return (
            DocumentStatus.PENDING,
            DocumentStatus.STORED,
            DocumentStatus.QUEUED,
            DocumentStatus.EXTRACTING,
            DocumentStatus.CHUNKING,
            DocumentStatus.EMBEDDING,
        )

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0.0

    @staticmethod
    def _average(values: list[int]) -> float:
        return float(fmean(values)) if values else 0.0

    @staticmethod
    def _percentile(values: list[int], percentile_value: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = (len(ordered) - 1) * percentile_value
        lower = int(index)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = index - lower
        return float(
            ordered[lower]
            + (ordered[upper] - ordered[lower]) * fraction
        )
