from uuid import UUID

from celery import Celery

from secure_knowledge_core.core.settings import get_settings


class CeleryIngestionTaskQueue:
    task_name = "secure_knowledge_worker.ingest_document_version"

    def __init__(self) -> None:
        settings = get_settings()
        self.client = Celery(
            "secure-knowledge-api",
            broker=settings.redis_url,
        )

    def enqueue_document_ingestion(
        self,
        *,
        document_version_id: UUID,
    ) -> None:
        self.client.send_task(
            self.task_name,
            kwargs={"document_version_id": str(document_version_id)},
        )
