from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from secure_knowledge_core.database.enums import (
    Answerability,
    AnswerGenerationStatus,
    ExecutionMode,
)
from secure_knowledge_core.database.models import (
    AnswerRun,
    DailyOrganizationMetric,
    Organization,
    RetrievalRun,
)


@dataclass
class _DailyAccumulator:
    query_count: int = 0
    answer_count: int = 0
    abstention_count: int = 0
    failure_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_microusd: int = 0
    retrieval_latency_sum_ms: int = 0
    generation_latency_sum_ms: int = 0
    total_latency_sum_ms: int = 0


class DailyMetricAggregationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def rebuild_date(self, *, metric_date: date) -> int:
        start = datetime.combine(metric_date, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)
        organization_ids = list(self.session.scalars(select(Organization.id)))
        accumulators = {
            organization_id: _DailyAccumulator()
            for organization_id in organization_ids
        }
        rows = self.session.execute(
            select(AnswerRun, RetrievalRun)
            .join(RetrievalRun, RetrievalRun.id == AnswerRun.retrieval_run_id)
            .where(
                AnswerRun.execution_mode == ExecutionMode.PRODUCTION,
                RetrievalRun.execution_mode == ExecutionMode.PRODUCTION,
                AnswerRun.organization_id == RetrievalRun.organization_id,
                AnswerRun.created_at >= start,
                AnswerRun.created_at < end,
            )
        )
        for answer_run, retrieval_run in rows:
            accumulator = accumulators.setdefault(
                answer_run.organization_id,
                _DailyAccumulator(),
            )
            accumulator.query_count += 1
            if answer_run.status == AnswerGenerationStatus.FAILED:
                accumulator.failure_count += 1
            elif (
                answer_run.status == AnswerGenerationStatus.COMPLETED
                and answer_run.answerability == Answerability.NOT_FOUND
            ):
                accumulator.abstention_count += 1
            elif (
                answer_run.status == AnswerGenerationStatus.COMPLETED
                and answer_run.answerability
                in {
                    Answerability.ANSWERABLE,
                    Answerability.PARTIALLY_ANSWERABLE,
                    Answerability.AMBIGUOUS,
                }
            ):
                accumulator.answer_count += 1

            retrieval_duration = retrieval_run.duration_ms
            generation_duration = answer_run.generation_duration_ms or 0
            accumulator.input_tokens += answer_run.input_tokens or 0
            accumulator.output_tokens += answer_run.output_tokens or 0
            accumulator.estimated_cost_microusd += (
                answer_run.estimated_cost_microusd or 0
            )
            accumulator.retrieval_latency_sum_ms += retrieval_duration
            accumulator.generation_latency_sum_ms += generation_duration
            accumulator.total_latency_sum_ms += (
                retrieval_duration + generation_duration
            )

        self.session.execute(
            delete(DailyOrganizationMetric).where(
                DailyOrganizationMetric.metric_date == metric_date
            )
        )
        self.session.add_all(
            [
                DailyOrganizationMetric(
                    organization_id=organization_id,
                    metric_date=metric_date,
                    query_count=values.query_count,
                    answer_count=values.answer_count,
                    abstention_count=values.abstention_count,
                    failure_count=values.failure_count,
                    input_tokens=values.input_tokens,
                    output_tokens=values.output_tokens,
                    estimated_cost_microusd=(
                        values.estimated_cost_microusd
                    ),
                    retrieval_latency_sum_ms=(
                        values.retrieval_latency_sum_ms
                    ),
                    generation_latency_sum_ms=(
                        values.generation_latency_sum_ms
                    ),
                    total_latency_sum_ms=values.total_latency_sum_ms,
                )
                for organization_id, values in accumulators.items()
            ]
        )
        self.session.flush()
        return len(accumulators)
