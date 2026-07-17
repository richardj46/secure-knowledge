from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete, exists, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from secure_knowledge_core.core.settings import Settings, get_settings
from secure_knowledge_core.database.models import (
    AnswerRun,
    AuditEvent,
    EvaluationCaseResult,
    EvaluationRun,
    RetrievalResultRecord,
    RetrievalRun,
)


@dataclass(frozen=True)
class RetentionCleanupResult:
    cutoff: datetime | None
    deleted_detail_rows: int
    deleted_summary_rows: int = 0

    @property
    def deleted_rows(self) -> int:
        return self.deleted_detail_rows + self.deleted_summary_rows


class RetentionService:
    """Delete expired trace detail while retaining aggregate metrics."""

    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()

    def cleanup_expired_retrieval_traces(
        self,
        *,
        now: datetime | None = None,
    ) -> RetentionCleanupResult:
        cutoff = self._cutoff(
            days=self.settings.retrieval_trace_retention_days,
            now=now,
        )
        expired_run_ids = select(RetrievalRun.id).where(
            RetrievalRun.created_at < cutoff
        )
        detail_result = self.session.execute(
            delete(RetrievalResultRecord)
            .where(
                RetrievalResultRecord.retrieval_run_id.in_(expired_run_ids)
            )
            .execution_options(synchronize_session=False)
        )

        # Answer runs retain their retrieval summary for the full answer-trace
        # retention period. Unreferenced summaries can be removed immediately.
        answer_reference = exists(
            select(1).where(
                AnswerRun.retrieval_run_id == RetrievalRun.id
            )
        ).correlate(RetrievalRun)
        summary_result = self.session.execute(
            delete(RetrievalRun)
            .where(
                RetrievalRun.created_at < cutoff,
                ~answer_reference,
            )
            .execution_options(synchronize_session=False)
        )
        return RetentionCleanupResult(
            cutoff=cutoff,
            deleted_detail_rows=self._row_count(detail_result),
            deleted_summary_rows=self._row_count(summary_result),
        )

    def cleanup_expired_answer_traces(
        self,
        *,
        now: datetime | None = None,
    ) -> RetentionCleanupResult:
        cutoff = self._cutoff(
            days=self.settings.answer_trace_retention_days,
            now=now,
        )
        result = self.session.execute(
            delete(AnswerRun)
            .where(AnswerRun.created_at < cutoff)
            .execution_options(synchronize_session=False)
        )
        return RetentionCleanupResult(
            cutoff=cutoff,
            deleted_detail_rows=self._row_count(result),
        )

    def cleanup_expired_evaluation_details(
        self,
        *,
        now: datetime | None = None,
    ) -> RetentionCleanupResult:
        cutoff = self._cutoff(
            days=self.settings.evaluation_result_retention_days,
            now=now,
        )
        expired_run_ids = select(EvaluationRun.id).where(
            EvaluationRun.created_at < cutoff
        )
        result = self.session.execute(
            delete(EvaluationCaseResult)
            .where(
                EvaluationCaseResult.evaluation_run_id.in_(expired_run_ids)
            )
            .execution_options(synchronize_session=False)
        )
        return RetentionCleanupResult(
            cutoff=cutoff,
            deleted_detail_rows=self._row_count(result),
        )

    def cleanup_expired_audit_events(
        self,
        *,
        now: datetime | None = None,
    ) -> RetentionCleanupResult:
        current_time = now or datetime.now(UTC)
        organization_ids = self.session.scalars(
            select(AuditEvent.organization_id).distinct()
        ).all()
        deleted_rows = 0
        oldest_cutoff: datetime | None = None

        for organization_id in organization_ids:
            retention_days = self._audit_retention_days(organization_id)
            cutoff = current_time - timedelta(days=retention_days)
            if oldest_cutoff is None or cutoff < oldest_cutoff:
                oldest_cutoff = cutoff
            result = self.session.execute(
                delete(AuditEvent)
                .where(
                    AuditEvent.organization_id == organization_id,
                    AuditEvent.occurred_at < cutoff,
                )
                .execution_options(synchronize_session=False)
            )
            deleted_rows += self._row_count(result)

        return RetentionCleanupResult(
            cutoff=oldest_cutoff,
            deleted_detail_rows=deleted_rows,
        )

    def _audit_retention_days(self, organization_id: UUID) -> int:
        return self.settings.audit_event_retention_overrides.get(
            str(organization_id),
            self.settings.audit_event_retention_days,
        )

    @staticmethod
    def _cutoff(*, days: int, now: datetime | None) -> datetime:
        return (now or datetime.now(UTC)) - timedelta(days=days)

    @staticmethod
    def _row_count(result: CursorResult[Any]) -> int:
        return max(result.rowcount or 0, 0)
