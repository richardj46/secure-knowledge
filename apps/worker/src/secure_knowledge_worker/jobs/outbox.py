from uuid import UUID

from secure_knowledge_core.database.session import SessionFactory
from secure_knowledge_core.outbox.service import OutboxPublisher
from secure_knowledge_worker.celery_app import celery_app


class CeleryIngestionTaskQueue:
    task_name = "secure_knowledge_worker.ingest_document_version"

    def enqueue_document_ingestion(
        self,
        *,
        document_version_id: UUID,
    ) -> None:
        celery_app.send_task(
            self.task_name,
            kwargs={"document_version_id": str(document_version_id)},
        )


@celery_app.task(name="secure_knowledge_worker.publish_pending_outbox_events")
def publish_pending_outbox_events() -> int:
    with SessionFactory() as session:
        return OutboxPublisher(
            session=session,
            task_queue=CeleryIngestionTaskQueue(),
        ).publish_pending()
