from typing import Protocol
from uuid import UUID


class IngestionTaskQueue(Protocol):
    def enqueue_document_ingestion(
        self,
        *,
        document_version_id: UUID,
    ) -> None:
        ...
