from uuid import UUID

from secure_knowledge_core.database.session import SessionFactory
from secure_knowledge_core.ingestion.embeddings import GeminiEmbeddingProvider
from secure_knowledge_core.ingestion.exceptions import TransientIngestionError
from secure_knowledge_core.ingestion.service import DocumentIngestionService
from secure_knowledge_worker.celery_app import celery_app


@celery_app.task(
    name="secure_knowledge_worker.ingest_document_version",
    bind=True,
    autoretry_for=(TransientIngestionError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5,
)
def ingest_document_version(
    self,
    document_version_id: str,
) -> None:
    with SessionFactory() as session:
        service = DocumentIngestionService(
            session=session,
            embedding_provider=GeminiEmbeddingProvider(),
        )
        service.ingest(
            document_version_id=UUID(document_version_id),
            worker_task_id=self.request.id,
        )
