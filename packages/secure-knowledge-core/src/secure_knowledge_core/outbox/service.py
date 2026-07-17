from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from secure_knowledge_core.database.enums import (
    DocumentStatus,
    DocumentVersionStatus,
)
from secure_knowledge_core.database.models import (
    Document,
    DocumentVersion,
    EvaluationRun,
    OutboxEvent,
)
from secure_knowledge_core.evaluations.queue import (
    EVALUATION_RUN_REQUESTED,
    EvaluationTaskQueue,
)
from secure_knowledge_core.ingestion.queue import IngestionTaskQueue

DOCUMENT_VERSION_INGESTION_REQUESTED = "document_version.ingestion_requested"


class OutboxPublisher:
    def __init__(
        self,
        *,
        session: Session,
        task_queue: IngestionTaskQueue,
        evaluation_task_queue: EvaluationTaskQueue | None = None,
    ) -> None:
        self.session = session
        self.task_queue = task_queue
        self.evaluation_task_queue = evaluation_task_queue

    def publish_event(self, *, event_id: UUID) -> bool:
        event = self.session.scalar(
            select(OutboxEvent)
            .where(
                OutboxEvent.id == event_id,
                OutboxEvent.published_at.is_(None),
            )
            .with_for_update()
        )
        if event is None:
            return True

        return self._publish_locked_event(event)

    def publish_pending(self, *, limit: int = 100) -> int:
        published_count = 0
        processed_ids: list[UUID] = []

        for _ in range(limit):
            statement = (
                select(OutboxEvent)
                .where(
                    OutboxEvent.published_at.is_(None),
                    OutboxEvent.event_type.in_(
                        (
                            DOCUMENT_VERSION_INGESTION_REQUESTED,
                            EVALUATION_RUN_REQUESTED,
                        )
                    ),
                )
                .order_by(OutboxEvent.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if processed_ids:
                statement = statement.where(OutboxEvent.id.not_in(processed_ids))

            event = self.session.scalar(statement)
            if event is None:
                self.session.rollback()
                break

            processed_ids.append(event.id)
            if self._publish_locked_event(event):
                published_count += 1

        return published_count

    def _publish_locked_event(self, event: OutboxEvent) -> bool:
        if event.event_type not in {
            DOCUMENT_VERSION_INGESTION_REQUESTED,
            EVALUATION_RUN_REQUESTED,
        }:
            return False

        try:
            self._enqueue_event(event)
        except Exception as exc:
            event.attempt_count += 1
            event.last_error = str(exc)[:2000]
            try:
                self.session.commit()
            except Exception:
                self.session.rollback()
            return False

        event.published_at = datetime.now(UTC)
        event.attempt_count += 1
        event.last_error = None

        self.session.commit()
        return True

    def _enqueue_event(self, event: OutboxEvent) -> None:
        if event.event_type == DOCUMENT_VERSION_INGESTION_REQUESTED:
            self._enqueue_document_ingestion(event)
            return

        if self.evaluation_task_queue is None:
            raise RuntimeError("Evaluation task queue is not configured.")

        evaluation_run_id = UUID(event.payload["evaluation_run_id"])
        if self.session.get(EvaluationRun, evaluation_run_id) is None:
            raise ValueError("Evaluation run no longer exists.")

        self.evaluation_task_queue.enqueue_evaluation_run(
            evaluation_run_id=evaluation_run_id,
        )

    def _enqueue_document_ingestion(self, event: OutboxEvent) -> None:
        document_version_id = UUID(event.payload["document_version_id"])
        document_version = self.session.get(
            DocumentVersion,
            document_version_id,
        )
        if document_version is None:
            raise ValueError("Document version no longer exists.")

        self.task_queue.enqueue_document_ingestion(
            document_version_id=document_version_id,
        )

        document = self.session.get(Document, document_version.document_id)
        if document_version.status in {
            DocumentVersionStatus.PENDING,
            DocumentVersionStatus.FAILED,
        }:
            document_version.status = DocumentVersionStatus.QUEUED
            document_version.processing_stage = DocumentVersionStatus.QUEUED
            if (
                document is not None
                and document.current_version_number
                == document_version.version_number
            ):
                document.status = DocumentStatus.QUEUED
