from sqlalchemy import select
from sqlalchemy.orm import Session

from secure_knowledge_core.answers.exceptions import CitationValidationError
from secure_knowledge_core.core.tracing import set_span_attributes, start_span
from secure_knowledge_core.database.enums import (
    EvaluationCaseStatus,
    ExecutionMode,
)
from secure_knowledge_core.database.models import (
    Conversation,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationRun,
)
from secure_knowledge_core.evaluations.datasets.schemas import (
    EvaluationCaseDefinition,
)
from secure_knowledge_core.evaluations.exceptions import (
    as_transient_evaluation_error,
    evaluation_failure_code,
)
from secure_knowledge_core.evaluations.graders.interface import EvaluationGrader


class EvaluationRunner:
    def __init__(
        self,
        *,
        session: Session,
        retrieval_service_factory,
        answer_service_factory,
        graders: list[EvaluationGrader],
    ) -> None:
        self.session = session
        self.retrieval_service_factory = (
            retrieval_service_factory
        )
        self.answer_service_factory = answer_service_factory
        self.graders = graders

    def run_case(
        self,
        *,
        evaluation_run: EvaluationRun,
        evaluation_case: EvaluationCase,
    ) -> EvaluationCaseResult:
        with start_span(
            "evaluation.run_case",
            {
                "organization_id": evaluation_run.organization_id,
                "evaluation_run_id": evaluation_run.id,
                "evaluation_case_id": evaluation_case.id,
                "model": evaluation_run.answer_model,
            },
        ) as span:
            result = self._run_case(
                evaluation_run=evaluation_run,
                evaluation_case=evaluation_case,
            )
            set_span_attributes(span, {"status": result.status})
            return result

    def _run_case(
        self,
        *,
        evaluation_run: EvaluationRun,
        evaluation_case: EvaluationCase,
    ) -> EvaluationCaseResult:
        definition = (
            EvaluationCaseDefinition.model_validate(
                evaluation_case.definition
            )
        )

        result = self.session.scalar(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == evaluation_run.id,
                EvaluationCaseResult.evaluation_case_id == evaluation_case.id,
            )
        )
        if result is not None and result.status in {
            EvaluationCaseStatus.PASSED,
            EvaluationCaseStatus.FAILED,
            EvaluationCaseStatus.ERROR,
        }:
            return result
        if result is None:
            result = EvaluationCaseResult(
                evaluation_run_id=evaluation_run.id,
                evaluation_case_id=evaluation_case.id,
                status=EvaluationCaseStatus.RUNNING,
            )
            self.session.add(result)
        else:
            result.status = EvaluationCaseStatus.RUNNING
            result.error_code = None
            result.error_message = None

        self.session.commit()

        try:
            conversation = self._create_isolated_conversation(
                definition=definition,
                result=result,
            )
            execution = self._execute_case(
                definition,
                conversation_id=conversation.id,
            )

            with start_span(
                "evaluation.grade",
                {
                    "organization_id": evaluation_run.organization_id,
                    "evaluation_run_id": evaluation_run.id,
                    "evaluation_case_id": evaluation_case.id,
                    "model": evaluation_run.answer_model,
                },
            ):
                deterministic_metrics = self._calculate_deterministic_metrics(
                    definition=definition,
                    execution=execution,
                )
                grader_results = self._run_graders(
                    definition=definition,
                    execution=execution,
                )

            passed = self._determine_case_pass(
                deterministic_metrics=deterministic_metrics,
                grader_results=grader_results,
            )

            self._persist_case_success(
                result=result,
                execution=execution,
                metrics=deterministic_metrics,
                grader_results=grader_results,
                passed=passed,
            )

        except Exception as exc:
            transient = as_transient_evaluation_error(exc)
            if transient is not None:
                self._prepare_case_retry(result=result)
                raise transient from exc

            self._persist_case_error(
                result=result,
                error_code=evaluation_failure_code(exc),
                semantic_failure=isinstance(exc, CitationValidationError),
            )

        return result

    def _create_isolated_conversation(
        self,
        *,
        definition: EvaluationCaseDefinition,
        result: EvaluationCaseResult,
    ) -> Conversation:
        conversation = Conversation(
            organization_id=definition.organization_id,
            user_id=definition.user_id,
            title=None,
            execution_mode=ExecutionMode.EVALUATION,
            is_evaluation=True,
            evaluation_case_result_id=result.id,
        )
        self.session.add(conversation)
        self.session.commit()
        return conversation

    def _prepare_case_retry(self, *, result: EvaluationCaseResult) -> None:
        self.session.rollback()
        retry_result = self.session.get(EvaluationCaseResult, result.id)
        if retry_result is None:
            return

        conversation = self.session.scalar(
            select(Conversation).where(
                Conversation.evaluation_case_result_id == retry_result.id
            )
        )
        if conversation is not None:
            self.session.delete(conversation)

        retry_result.status = EvaluationCaseStatus.PENDING
        retry_result.retrieval_run_id = None
        retry_result.answer_run_id = None
        retry_result.error_code = "transient_infrastructure_error"
        retry_result.error_message = None
        self.session.commit()

    def _persist_case_error(
        self,
        *,
        result: EvaluationCaseResult,
        error_code: str,
        semantic_failure: bool,
    ) -> None:
        self.session.rollback()
        failed_result = self.session.get(EvaluationCaseResult, result.id)
        if failed_result is None:
            return

        failed_result.status = (
            EvaluationCaseStatus.FAILED
            if semantic_failure
            else EvaluationCaseStatus.ERROR
        )
        failed_result.error_code = (
            "citation_validation_failed"
            if semantic_failure
            else error_code
        )
        failed_result.error_message = "Evaluation case execution failed."
        self.session.commit()
