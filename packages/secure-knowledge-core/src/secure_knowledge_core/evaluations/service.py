from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.database.enums import (
    EvaluationCaseStatus,
    EvaluationRunStatus,
    HumanReviewStatus,
    OrganizationRole,
)
from secure_knowledge_core.database.models import (
    AnswerCitation,
    Document,
    DocumentChunk,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationDataset,
    EvaluationGraderResult,
    EvaluationMetricResult,
    EvaluationRun,
    OrganizationMembership,
    OutboxEvent,
    Workspace,
)
from secure_knowledge_core.evaluations.datasets.schemas import (
    EvaluationCaseDefinition,
)
from secure_knowledge_core.evaluations.exceptions import (
    EvaluationAccessDeniedError,
    EvaluationBaselineRunNotFoundError,
    EvaluationBaselineRunNotReadyError,
    EvaluationCaseResultNotFoundError,
    EvaluationCaseScopeError,
    EvaluationDatasetConflictError,
    EvaluationDatasetNotFoundError,
    EvaluationDatasetReleasedError,
    EvaluationLiveDatasetTooLargeError,
    EvaluationRunnerConfigurationError,
    EvaluationRunNotFoundError,
    TransientEvaluationError,
    as_transient_evaluation_error,
)
from secure_knowledge_core.evaluations.metrics.aggregation import (
    aggregate_run_metrics,
)
from secure_knowledge_core.evaluations.metrics.regression import (
    BaselineComparison,
    RegressionLimits,
    compare_to_baseline,
)
from secure_knowledge_core.evaluations.metrics.thresholds import (
    HARD_GATE_METRICS,
    EvaluationThresholds,
    determine_run_pass,
    evaluate_thresholds,
)
from secure_knowledge_core.evaluations.modes import EvaluationRunMode
from secure_knowledge_core.evaluations.queue import EVALUATION_RUN_REQUESTED
from secure_knowledge_core.evaluations.schemas import (
    EvaluationCaseReviewRead,
    EvaluationGraderResultRead,
    EvaluationMetricResultRead,
    EvaluationReviewCitation,
    EvaluationReviewPassage,
    HumanReviewUpdate,
)
from secure_knowledge_core.versioning import (
    ANSWER_PROMPT_VERSION,
    AUTHORIZATION_POLICY_VERSION,
    CHUNKING_VERSION,
    GROUNDEDNESS_GRADER_VERSION,
    RETRIEVAL_CONFIGURATION_VERSION,
)


class EvaluationCaseRunner(Protocol):
    def run_case(
        self,
        *,
        evaluation_run: EvaluationRun,
        evaluation_case: EvaluationCase,
    ) -> EvaluationCaseResult:
        ...


class EvaluationService:
    def __init__(
        self,
        *,
        session: Session,
        case_runner: EvaluationCaseRunner | None = None,
    ) -> None:
        self.session = session
        self.case_runner = case_runner

    def create_run(
        self,
        *,
        dataset_id: UUID,
        started_by_user_id: UUID,
        baseline_run_id: UUID | None,
        configuration: dict[str, Any],
        code_revision: str | None,
    ) -> EvaluationRun:
        dataset = self.session.get(EvaluationDataset, dataset_id)
        if dataset is None or not dataset.is_active:
            raise EvaluationDatasetNotFoundError

        self._require_evaluation_administrator(
            organization_id=dataset.organization_id,
            user_id=started_by_user_id,
        )
        baseline_run = self._resolve_baseline_run(
            baseline_run_id=baseline_run_id,
            dataset=dataset,
        )

        configuration_snapshot = dict(configuration)
        settings = get_settings()
        thresholds = EvaluationThresholds.model_validate(
            configuration_snapshot.get("thresholds", {})
        )
        configuration_snapshot["thresholds"] = thresholds.model_dump()
        regression_limits = RegressionLimits.model_validate(
            configuration_snapshot.get("regression_limits", {})
        )
        configuration_snapshot["regression_limits"] = (
            regression_limits.model_dump()
        )

        total_cases = self.session.scalar(
            select(func.count(EvaluationCase.id)).where(
                EvaluationCase.dataset_id == dataset.id
            )
        )
        if (
            configuration_snapshot.get("mode")
            == EvaluationRunMode.LIVE.value
            and (total_cases or 0)
            > settings.evaluation_live_maximum_cases
        ):
            raise EvaluationLiveDatasetTooLargeError

        run = EvaluationRun(
            dataset_id=dataset.id,
            organization_id=dataset.organization_id,
            started_by_user_id=started_by_user_id,
            baseline_run_id=(baseline_run.id if baseline_run else None),
            status=EvaluationRunStatus.PENDING,
            configuration=configuration_snapshot,
            code_revision=code_revision,
            answer_prompt_version=ANSWER_PROMPT_VERSION,
            grader_prompt_version=GROUNDEDNESS_GRADER_VERSION,
            answer_model=configuration_snapshot.get("answer_model"),
            embedding_model=str(
                configuration_snapshot.get("embedding_model")
                or settings.embedding_model
            ),
            reranker_model=settings.reranker_model,
            chunking_version=CHUNKING_VERSION,
            retrieval_configuration_version=(
                RETRIEVAL_CONFIGURATION_VERSION
            ),
            authorization_policy_version=AUTHORIZATION_POLICY_VERSION,
            total_cases=total_cases or 0,
            completed_cases=0,
            passed_cases=0,
            failed_cases=0,
        )
        self.session.add(run)
        self.session.flush()
        self.session.add(
            OutboxEvent(
                event_type=EVALUATION_RUN_REQUESTED,
                aggregate_type="evaluation_run",
                aggregate_id=run.id,
                payload={"evaluation_run_id": str(run.id)},
            )
        )
        self.session.flush()
        return run

    def _resolve_baseline_run(
        self,
        *,
        baseline_run_id: UUID | None,
        dataset: EvaluationDataset,
    ) -> EvaluationRun | None:
        if baseline_run_id is None:
            return None

        baseline_run = self.session.get(EvaluationRun, baseline_run_id)
        if (
            baseline_run is None
            or baseline_run.organization_id != dataset.organization_id
            or baseline_run.dataset_id != dataset.id
        ):
            raise EvaluationBaselineRunNotFoundError
        if baseline_run.status != EvaluationRunStatus.SUCCEEDED:
            raise EvaluationBaselineRunNotReadyError
        return baseline_run

    def create_dataset(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        name: str,
        description: str | None,
        version: int,
    ) -> EvaluationDataset:
        self._require_evaluation_administrator(
            organization_id=organization_id,
            user_id=user_id,
        )
        dataset = EvaluationDataset(
            organization_id=organization_id,
            name=name,
            description=description,
            version=version,
            is_active=True,
        )
        self.session.add(dataset)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise EvaluationDatasetConflictError from exc
        return dataset

    def import_cases(
        self,
        *,
        dataset_id: UUID,
        user_id: UUID,
        definitions: list[EvaluationCaseDefinition],
    ) -> list[EvaluationCase]:
        dataset = self.get_dataset(dataset_id=dataset_id, user_id=user_id)
        released = self.session.scalar(
            select(EvaluationRun.id)
            .where(EvaluationRun.dataset_id == dataset.id)
            .limit(1)
        )
        if released is not None:
            raise EvaluationDatasetReleasedError

        self._validate_case_scopes(dataset=dataset, definitions=definitions)
        cases = [
            EvaluationCase(
                dataset_id=dataset.id,
                external_id=definition.external_id,
                name=definition.name,
                user_id=definition.user_id,
                organization_id=definition.organization_id,
                question=definition.question,
                definition=definition.model_dump(mode="json"),
                tags=list(definition.tags),
            )
            for definition in definitions
        ]
        self.session.add_all(cases)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise EvaluationDatasetConflictError from exc
        return cases

    def get_dataset(
        self,
        *,
        dataset_id: UUID,
        user_id: UUID,
    ) -> EvaluationDataset:
        dataset = self.session.get(EvaluationDataset, dataset_id)
        if dataset is None:
            raise EvaluationDatasetNotFoundError
        self._require_evaluation_administrator(
            organization_id=dataset.organization_id,
            user_id=user_id,
        )
        return dataset

    def list_cases(
        self,
        *,
        dataset_id: UUID,
        user_id: UUID,
    ) -> list[EvaluationCase]:
        dataset = self.get_dataset(dataset_id=dataset_id, user_id=user_id)
        return list(
            self.session.scalars(
                select(EvaluationCase)
                .where(EvaluationCase.dataset_id == dataset.id)
                .order_by(EvaluationCase.created_at, EvaluationCase.id)
            )
        )

    def get_run(
        self,
        *,
        evaluation_run_id: UUID,
        user_id: UUID,
    ) -> EvaluationRun:
        run = self.session.get(EvaluationRun, evaluation_run_id)
        if run is None:
            raise EvaluationRunNotFoundError
        self._require_evaluation_administrator(
            organization_id=run.organization_id,
            user_id=user_id,
        )
        return run

    def list_results(
        self,
        *,
        evaluation_run_id: UUID,
        user_id: UUID,
    ) -> list[EvaluationCaseResult]:
        run = self.get_run(
            evaluation_run_id=evaluation_run_id,
            user_id=user_id,
        )
        return list(
            self.session.scalars(
                select(EvaluationCaseResult)
                .where(EvaluationCaseResult.evaluation_run_id == run.id)
                .order_by(EvaluationCaseResult.created_at)
            )
        )

    def list_metrics(
        self,
        *,
        evaluation_run_id: UUID,
        user_id: UUID,
    ) -> list[EvaluationMetricResult]:
        run = self.get_run(
            evaluation_run_id=evaluation_run_id,
            user_id=user_id,
        )
        return list(
            self.session.scalars(
                select(EvaluationMetricResult)
                .where(EvaluationMetricResult.evaluation_run_id == run.id)
                .order_by(
                    EvaluationMetricResult.evaluation_case_result_id,
                    EvaluationMetricResult.metric_name,
                )
            )
        )

    def get_case_review(
        self,
        *,
        evaluation_case_result_id: UUID,
        user_id: UUID,
    ) -> EvaluationCaseReviewRead:
        result, evaluation_case, evaluation_run = self._get_reviewable_case_result(
            evaluation_case_result_id=evaluation_case_result_id,
            user_id=user_id,
        )
        definition = EvaluationCaseDefinition.model_validate(
            evaluation_case.definition
        )
        retrieved_chunk_ids = [
            UUID(str(value)) for value in result.retrieved_chunk_ids
        ]
        context_chunk_ids = [
            UUID(str(value)) for value in result.context_chunk_ids
        ]
        all_passages = self._load_review_passages(
            organization_id=evaluation_run.organization_id,
            values=[
                str(chunk_id)
                for chunk_id in dict.fromkeys(
                    [*retrieved_chunk_ids, *context_chunk_ids]
                )
            ]
        )
        passages_by_id = {
            passage.chunk_id: passage for passage in all_passages
        }
        retrieved_passages = [
            passages_by_id[chunk_id]
            for chunk_id in retrieved_chunk_ids
            if chunk_id in passages_by_id
        ]
        selected_context = [
            passages_by_id[chunk_id]
            for chunk_id in context_chunk_ids
            if chunk_id in passages_by_id
        ]

        metric_records = self.session.scalars(
            select(EvaluationMetricResult)
            .where(
                EvaluationMetricResult.evaluation_case_result_id == result.id
            )
            .order_by(EvaluationMetricResult.metric_name)
        ).all()
        grader_records = self.session.scalars(
            select(EvaluationGraderResult)
            .where(
                EvaluationGraderResult.evaluation_case_result_id == result.id
            )
            .order_by(
                EvaluationGraderResult.grader_name,
                EvaluationGraderResult.claim_index,
                EvaluationGraderResult.id,
            )
        ).all()

        return EvaluationCaseReviewRead(
            evaluation_case_result_id=result.id,
            evaluation_run_id=result.evaluation_run_id,
            question=definition.question,
            expected_answerability=definition.expected_answerability.value,
            retrieved_chunk_ids=retrieved_chunk_ids,
            selected_context_chunk_ids=context_chunk_ids,
            retrieved_passages=retrieved_passages,
            selected_context=selected_context,
            generated_answer=result.actual_answer,
            citations=self._load_review_citations(
                answer_run_id=result.answer_run_id,
                organization_id=evaluation_run.organization_id,
            ),
            deterministic_metrics=[
                EvaluationMetricResultRead.model_validate(record)
                for record in metric_records
            ],
            model_grades=[
                EvaluationGraderResultRead.model_validate(record)
                for record in grader_records
            ],
            human_review_status=result.human_review_status,
            human_score=result.human_score,
            human_notes=result.human_notes,
            reviewed_by_user_id=result.reviewed_by_user_id,
            reviewed_at=result.reviewed_at,
        )

    def update_case_review(
        self,
        *,
        evaluation_case_result_id: UUID,
        user_id: UUID,
        review: HumanReviewUpdate,
    ) -> EvaluationCaseReviewRead:
        result, _, _ = self._get_reviewable_case_result(
            evaluation_case_result_id=evaluation_case_result_id,
            user_id=user_id,
        )
        result.human_review_status = review.status
        result.human_score = review.score
        result.human_notes = review.notes
        if review.status == HumanReviewStatus.PENDING:
            result.reviewed_by_user_id = None
            result.reviewed_at = None
        else:
            result.reviewed_by_user_id = user_id
            result.reviewed_at = datetime.now(UTC)
        self.session.flush()
        return self.get_case_review(
            evaluation_case_result_id=result.id,
            user_id=user_id,
        )

    def _get_reviewable_case_result(
        self,
        *,
        evaluation_case_result_id: UUID,
        user_id: UUID,
    ) -> tuple[EvaluationCaseResult, EvaluationCase, EvaluationRun]:
        result = self.session.get(
            EvaluationCaseResult,
            evaluation_case_result_id,
        )
        if result is None:
            raise EvaluationCaseResultNotFoundError
        run = self.get_run(
            evaluation_run_id=result.evaluation_run_id,
            user_id=user_id,
        )
        evaluation_case = self.session.get(
            EvaluationCase,
            result.evaluation_case_id,
        )
        if evaluation_case is None or evaluation_case.dataset_id != run.dataset_id:
            raise EvaluationCaseResultNotFoundError
        return result, evaluation_case, run

    def _load_review_passages(
        self,
        *,
        organization_id: UUID,
        values: list[str],
    ) -> list[EvaluationReviewPassage]:
        chunk_ids = [UUID(str(value)) for value in values]
        if not chunk_ids:
            return []
        rows = self.session.execute(
            select(DocumentChunk, Document.title)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.organization_id == organization_id,
                DocumentChunk.id.in_(chunk_ids),
            )
        ).all()
        passages_by_id = {
            chunk.id: EvaluationReviewPassage(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=document_title,
                content=chunk.content,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
            )
            for chunk, document_title in rows
        }
        return [
            passages_by_id[chunk_id]
            for chunk_id in chunk_ids
            if chunk_id in passages_by_id
        ]

    def _load_review_citations(
        self,
        *,
        answer_run_id: UUID | None,
        organization_id: UUID,
    ) -> list[EvaluationReviewCitation]:
        if answer_run_id is None:
            return []
        rows = self.session.execute(
            select(
                AnswerCitation,
                Document.title,
                DocumentChunk.page_number,
            )
            .join(Document, Document.id == AnswerCitation.document_id)
            .join(DocumentChunk, DocumentChunk.id == AnswerCitation.chunk_id)
            .where(
                AnswerCitation.answer_run_id == answer_run_id,
                Document.organization_id == organization_id,
            )
            .order_by(AnswerCitation.citation_index)
        ).all()
        return [
            EvaluationReviewCitation(
                citation_index=citation.citation_index,
                chunk_id=citation.chunk_id,
                document_id=citation.document_id,
                document_title=document_title,
                page_number=page_number,
                claims=citation.claims,
            )
            for citation, document_title, page_number in rows
        ]

    def _require_evaluation_administrator(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
    ) -> None:
        role = self.session.scalar(
            select(OrganizationMembership.role).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        if role not in {
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
            OrganizationRole.EVALUATION_ADMIN,
        }:
            raise EvaluationAccessDeniedError

    def _validate_case_scopes(
        self,
        *,
        dataset: EvaluationDataset,
        definitions: list[EvaluationCaseDefinition],
    ) -> None:
        if any(
            definition.organization_id != dataset.organization_id
            for definition in definitions
        ):
            raise EvaluationCaseScopeError

        user_ids = {definition.user_id for definition in definitions}
        member_user_ids = set(
            self.session.scalars(
                select(OrganizationMembership.user_id).where(
                    OrganizationMembership.organization_id
                    == dataset.organization_id,
                    OrganizationMembership.user_id.in_(user_ids),
                )
            )
        )
        if member_user_ids != user_ids:
            raise EvaluationCaseScopeError

        workspace_ids = {
            workspace_id
            for definition in definitions
            for workspace_id in definition.workspace_ids
        }
        if not workspace_ids:
            return
        scoped_workspace_ids = set(
            self.session.scalars(
                select(Workspace.id).where(
                    Workspace.organization_id == dataset.organization_id,
                    Workspace.id.in_(workspace_ids),
                )
            )
        )
        if scoped_workspace_ids != workspace_ids:
            raise EvaluationCaseScopeError

    def execute_run(self, *, evaluation_run_id: UUID) -> None:
        run = self.session.scalar(
            select(EvaluationRun)
            .where(EvaluationRun.id == evaluation_run_id)
            .with_for_update()
        )
        if run is None:
            raise EvaluationRunNotFoundError
        if run.status in {
            EvaluationRunStatus.SUCCEEDED,
            EvaluationRunStatus.CANCELLED,
        }:
            return

        run.status = EvaluationRunStatus.RUNNING
        run.started_at = run.started_at or datetime.now(UTC)
        run.failure_message = None
        self.session.commit()

        try:
            self._execute_cases(run)
            self._finish_run(run)
        except TransientEvaluationError:
            self.session.rollback()
            raise
        except Exception as exc:
            self.session.rollback()
            transient = as_transient_evaluation_error(exc)
            if transient is not None:
                raise transient from exc

            failed_run = self.session.get(EvaluationRun, evaluation_run_id)
            if failed_run is not None:
                failed_run.status = EvaluationRunStatus.FAILED
                failed_run.failure_message = "Evaluation execution failed."
                failed_run.completed_at = datetime.now(UTC)
                self.session.commit()
            raise

    def _execute_cases(self, run: EvaluationRun) -> None:
        cases = self.session.scalars(
            select(EvaluationCase)
            .where(EvaluationCase.dataset_id == run.dataset_id)
            .order_by(EvaluationCase.created_at, EvaluationCase.id)
        ).all()

        if cases and self.case_runner is None:
            raise EvaluationRunnerConfigurationError(
                "No evaluation case runner is configured."
            )

        for evaluation_case in cases:
            assert self.case_runner is not None
            existing_status = self.session.scalar(
                select(EvaluationCaseResult.status).where(
                    EvaluationCaseResult.evaluation_run_id == run.id,
                    EvaluationCaseResult.evaluation_case_id
                    == evaluation_case.id,
                )
            )
            if existing_status in {
                EvaluationCaseStatus.PASSED,
                EvaluationCaseStatus.FAILED,
                EvaluationCaseStatus.ERROR,
            }:
                continue

            self.case_runner.run_case(
                evaluation_run=run,
                evaluation_case=evaluation_case,
            )

    def _finish_run(self, run: EvaluationRun) -> None:
        case_results = self.session.scalars(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == run.id
            )
        ).all()
        statuses = self.session.execute(
            select(EvaluationCaseResult.status, func.count())
            .where(EvaluationCaseResult.evaluation_run_id == run.id)
            .group_by(EvaluationCaseResult.status)
        ).all()
        counts = dict(statuses)
        run.completed_cases = sum(counts.values())
        run.passed_cases = counts.get(EvaluationCaseStatus.PASSED, 0)
        run.failed_cases = sum(
            counts.get(status, 0)
            for status in (
                EvaluationCaseStatus.FAILED,
                EvaluationCaseStatus.ERROR,
            )
        )
        (
            run.hard_gates_passed,
            run.quality_gates_passed,
            run.regression_passed,
        ) = self._persist_aggregate_metrics(
            run=run,
            case_results=case_results,
        )
        run.status = EvaluationRunStatus.SUCCEEDED
        run.completed_at = datetime.now(UTC)
        self.session.commit()

    def _persist_aggregate_metrics(
        self,
        *,
        run: EvaluationRun,
        case_results: list[EvaluationCaseResult],
    ) -> tuple[bool, bool, bool]:
        case_metric_values: dict[str, list[float]] = defaultdict(list)
        rows = self.session.execute(
            select(
                EvaluationMetricResult.metric_name,
                EvaluationMetricResult.value,
            ).where(
                EvaluationMetricResult.evaluation_run_id == run.id,
                EvaluationMetricResult.evaluation_case_result_id.is_not(None),
            )
        ).all()
        for metric_name, value in rows:
            case_metric_values[metric_name].append(float(value))

        aggregate = aggregate_run_metrics(
            case_results=case_results,
            case_metric_values=case_metric_values,
        )
        baseline_comparison = self._compare_with_baseline(
            run=run,
            current_values=aggregate.values,
        )
        thresholds = EvaluationThresholds.model_validate(
            run.configuration.get("thresholds", {})
        )
        decisions = evaluate_thresholds(
            values=aggregate.values,
            thresholds=thresholds,
        )
        case_hard_gates_passed = (
            all(result.hard_gates_passed is True for result in case_results)
            if case_results
            else True
        )
        hard_metric_gates_passed = all(
            decisions[metric_name].passed for metric_name in HARD_GATE_METRICS
        )
        hard_gates_passed = (
            case_hard_gates_passed and hard_metric_gates_passed
        )
        quality_gates_passed = all(
            decision.passed
            for metric_name, decision in decisions.items()
            if metric_name not in HARD_GATE_METRICS
        )
        aggregate_gate_passed = determine_run_pass(
            metrics=aggregate.values,
            thresholds=thresholds,
        )
        regression_passed = (
            case_hard_gates_passed
            and aggregate_gate_passed
            and quality_gates_passed
            and (
                baseline_comparison is None
                or baseline_comparison.passed
            )
        )
        self.session.execute(
            delete(EvaluationMetricResult).where(
                EvaluationMetricResult.evaluation_run_id == run.id,
                EvaluationMetricResult.evaluation_case_result_id.is_(None),
            )
        )
        self.session.add_all(
            [
                EvaluationMetricResult(
                    evaluation_run_id=run.id,
                    evaluation_case_result_id=None,
                    metric_name=metric_name,
                    metric_version="v1",
                    value=value,
                    passed=(
                        decisions[metric_name].passed
                        if metric_name in decisions
                        else None
                    ),
                    threshold=(
                        decisions[metric_name].threshold
                        if metric_name in decisions
                        else None
                    ),
                    details={
                        "unit": self._aggregate_metric_unit(metric_name),
                        "gate_type": (
                            "hard"
                            if metric_name in HARD_GATE_METRICS
                            else (
                                "quality"
                                if metric_name in decisions
                                else "informational"
                            )
                        ),
                        "comparison": (
                            decisions[metric_name].comparison
                            if metric_name in decisions
                            else None
                        ),
                    },
                )
                for metric_name, value in aggregate.values.items()
            ]
        )
        if baseline_comparison is not None:
            self.session.add_all(
                self._baseline_delta_records(
                    run=run,
                    comparison=baseline_comparison,
                )
            )
        self.session.add_all(
            [
                EvaluationMetricResult(
                    evaluation_run_id=run.id,
                    evaluation_case_result_id=None,
                    metric_name=metric_name,
                    metric_version="v1",
                    value=1.0 if passed else 0.0,
                    passed=passed,
                    threshold=1.0,
                    details={"unit": "boolean", "gate_type": gate_type},
                )
                for metric_name, passed, gate_type in (
                    ("hard_gates_passed", hard_gates_passed, "hard"),
                    ("quality_gates_passed", quality_gates_passed, "quality"),
                    ("regression_passed", regression_passed, "final"),
                )
            ]
        )
        return hard_gates_passed, quality_gates_passed, regression_passed

    def _compare_with_baseline(
        self,
        *,
        run: EvaluationRun,
        current_values: dict[str, float],
    ) -> BaselineComparison | None:
        if run.baseline_run_id is None:
            return None

        baseline_values = dict(
            self.session.execute(
                select(
                    EvaluationMetricResult.metric_name,
                    EvaluationMetricResult.value,
                ).where(
                    EvaluationMetricResult.evaluation_run_id
                    == run.baseline_run_id,
                    EvaluationMetricResult.evaluation_case_result_id.is_(None),
                )
            ).all()
        )
        limits = RegressionLimits.model_validate(
            run.configuration.get("regression_limits", {})
        )
        try:
            return compare_to_baseline(
                baseline={
                    name: float(value)
                    for name, value in baseline_values.items()
                },
                current=current_values,
                limits=limits,
            )
        except ValueError as exc:
            raise EvaluationRunnerConfigurationError(
                "The baseline run does not contain comparable metrics."
            ) from exc

    @staticmethod
    def _baseline_delta_records(
        *,
        run: EvaluationRun,
        comparison: BaselineComparison,
    ) -> list[EvaluationMetricResult]:
        return [
            EvaluationMetricResult(
                evaluation_run_id=run.id,
                evaluation_case_result_id=None,
                metric_name=f"baseline_delta.{metric_name}",
                metric_version="v1",
                value=delta.delta,
                passed=delta.passed,
                threshold=delta.limit,
                details={
                    "baseline_run_id": str(run.baseline_run_id),
                    "baseline_value": delta.baseline_value,
                    "current_value": delta.current_value,
                    "increase_ratio": delta.increase_ratio,
                    "comparison": delta.comparison,
                    "unit": EvaluationService._aggregate_metric_unit(
                        metric_name
                    ),
                    "gate_type": (
                        "regression"
                        if delta.passed is not None
                        else "informational"
                    ),
                },
            )
            for metric_name, delta in comparison.deltas.items()
        ]

    @staticmethod
    def _aggregate_metric_unit(metric_name: str) -> str:
        if metric_name in {
            "p50_latency",
            "p95_latency",
            "p95_latency_ms",
        }:
            return "milliseconds"
        if metric_name in {
            "average_cost",
            "average_cost_microusd",
            "total_cost",
        }:
            return "micro_usd"
        return "ratio"
