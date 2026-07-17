from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.core.tracing import set_span_attributes, start_span
from secure_knowledge_core.database.enums import (
    DocumentStatus,
    DocumentVersionStatus,
)
from secure_knowledge_core.database.models import (
    Document,
    DocumentChunk,
    DocumentProcessingAttempt,
    DocumentVersion,
)
from secure_knowledge_core.ingestion.chunking import ParagraphTokenChunker
from secure_knowledge_core.ingestion.embeddings import EmbeddingProvider
from secure_knowledge_core.ingestion.exceptions import (
    DocumentVersionNotFoundError,
    EmbeddingCountMismatchError,
    NoChunksGeneratedError,
    NoExtractableTextError,
    PermanentIngestionError,
    StorageDownloadError,
    TransientIngestionError,
    UnsupportedDocumentTypeError,
)
from secure_knowledge_core.ingestion.extractors.interface import (
    DocumentExtractor,
    ExtractedPage,
    ExtractionResult,
)
from secure_knowledge_core.ingestion.extractors.pdf import PdfExtractor
from secure_knowledge_core.ingestion.extractors.text import PlainTextExtractor
from secure_knowledge_core.ingestion.normalization import normalize_text
from secure_knowledge_core.storage.interface import ObjectStorage
from secure_knowledge_core.storage.s3 import S3ObjectStorage


class DocumentIngestionService:
    _active_statuses = {
        DocumentVersionStatus.EXTRACTING,
        DocumentVersionStatus.CHUNKING,
        DocumentVersionStatus.EMBEDDING,
    }

    def __init__(
        self,
        *,
        session: Session,
        embedding_provider: EmbeddingProvider,
        storage: ObjectStorage | None = None,
        chunker: ParagraphTokenChunker | None = None,
    ) -> None:
        self.session = session
        self._storage = storage
        self._chunker = chunker
        self.embedding_provider = embedding_provider
        self.extractors: dict[str, DocumentExtractor] = {
            "application/pdf": PdfExtractor(),
            "text/plain": PlainTextExtractor(),
        }

    def ingest(
        self,
        *,
        document_version_id: UUID,
        worker_task_id: str | None = None,
    ) -> None:
        version = self.session.get(
            DocumentVersion,
            document_version_id,
            with_for_update=True,
        )
        if version is None:
            self.session.rollback()
            raise DocumentVersionNotFoundError(
                f"Document version {document_version_id} was not found."
            )

        if version.status is DocumentVersionStatus.READY:
            self.session.rollback()
            return

        if version.status in self._active_statuses and self._lease_is_fresh(version):
            self.session.rollback()
            return

        document = self.session.get(Document, version.document_id)
        if document is None:
            self.session.rollback()
            raise DocumentVersionNotFoundError(
                f"Document for version {document_version_id} was not found."
            )

        attempt_id: UUID | None = None
        attempt_started_at = perf_counter()
        stage_started_at = attempt_started_at
        active_stage = "extraction"

        try:
            attempt = self._start_processing(
                version,
                document,
                worker_task_id=worker_task_id,
            )
            attempt_id = attempt.id
            stage_started_at = perf_counter()
            base_attributes = {
                "organization_id": document.organization_id,
                "workspace_id": document.workspace_id,
                "document_id": document.id,
                "document_version_id": version.id,
            }
            with start_span("ingestion.download", base_attributes):
                try:
                    content = self.storage.download(key=version.storage_key)
                except Exception:
                    raise StorageDownloadError from None
            with start_span("ingestion.extract", base_attributes):
                extractor = self._extractor_for(document.mime_type)
                extraction = extractor.extract(content)
                normalized_pages = self._normalize_pages(extraction)
                normalized_extraction = ExtractionResult(
                    pages=normalized_pages
                )
                total_text = normalized_extraction.full_text
            if len(total_text) < 20:
                raise NoExtractableTextError(
                    "The document contains too little extractable text."
                )

            attempt.extraction_duration_ms = self._duration_ms(stage_started_at)
            attempt.extracted_character_count = len(total_text)
            attempt.status = DocumentVersionStatus.CHUNKING.value
            self._set_stage(
                version,
                document,
                version_status=DocumentVersionStatus.CHUNKING,
                document_status=DocumentStatus.CHUNKING,
            )
            active_stage = "chunking"
            stage_started_at = perf_counter()
            with start_span(
                "ingestion.chunk",
                base_attributes,
            ) as chunk_span:
                chunks = self.chunker.chunk(normalized_extraction)
                set_span_attributes(
                    chunk_span,
                    {
                        "chunk_count": len(chunks),
                        "token_count": sum(
                            chunk.token_count for chunk in chunks
                        ),
                    },
                )
            if not chunks:
                raise NoChunksGeneratedError(
                    "The document produced no non-empty chunks."
                )

            attempt.chunking_duration_ms = self._duration_ms(stage_started_at)
            attempt.chunk_count = len(chunks)
            attempt.status = DocumentVersionStatus.EMBEDDING.value
            self._set_stage(
                version,
                document,
                version_status=DocumentVersionStatus.EMBEDDING,
                document_status=DocumentStatus.EMBEDDING,
            )
            active_stage = "embedding"
            stage_started_at = perf_counter()
            embedding_model = getattr(
                self.embedding_provider,
                "model",
                type(self.embedding_provider).__name__,
            )
            with start_span(
                "ingestion.embed",
                {
                    **base_attributes,
                    "model": embedding_model,
                    "chunk_count": len(chunks),
                    "token_count": sum(
                        chunk.token_count for chunk in chunks
                    ),
                },
            ):
                embeddings = self.embedding_provider.embed_texts(
                    [chunk.content for chunk in chunks]
                )
            if len(embeddings) != len(chunks):
                raise EmbeddingCountMismatchError(
                    "The embedding count does not match the chunk count."
                )
            attempt.embedding_duration_ms = self._duration_ms(stage_started_at)
            self.session.commit()
            active_stage = "finalizing"

            # The previous stage commit ended its transaction. This delete,
            # all inserts, and the READY transition share one final transaction.
            with start_span(
                "ingestion.persist",
                {
                    **base_attributes,
                    "chunk_count": len(chunks),
                    "token_count": sum(
                        chunk.token_count for chunk in chunks
                    ),
                },
            ):
                self.session.execute(
                    delete(DocumentChunk).where(
                        DocumentChunk.document_version_id == version.id
                    )
                )
                self.session.add_all(
                    [
                        DocumentChunk(
                            organization_id=document.organization_id,
                            workspace_id=document.workspace_id,
                            document_id=document.id,
                            document_version_id=version.id,
                            chunk_index=chunk.chunk_index,
                            content=chunk.content,
                            token_count=chunk.token_count,
                            page_number=chunk.page_number,
                            section_title=chunk.section_title,
                            chunk_metadata=chunk.metadata,
                            embedding=embedding,
                        )
                        for chunk, embedding in zip(
                            chunks,
                            embeddings,
                            strict=True,
                        )
                    ]
                )

                version.status = DocumentVersionStatus.READY
                version.processing_stage = DocumentVersionStatus.READY
                version.page_count = len(extraction.pages)
                version.extracted_character_count = len(total_text)
                version.chunk_count = len(chunks)
                version.processing_completed_at = datetime.now(UTC)
                version.failure_code = None
                version.failure_message = None
                attempt.status = "succeeded"
                attempt.completed_at = datetime.now(UTC)
                attempt.total_duration_ms = self._duration_ms(
                    attempt_started_at
                )
                self._set_current_document_status(
                    document,
                    version,
                    DocumentStatus.READY,
                )
                self.session.commit()
        except PermanentIngestionError as exc:
            self._record_failure(
                document_version_id=document_version_id,
                code=exc.code,
                message=exc.public_message,
                attempt_id=attempt_id,
                active_stage=active_stage,
                stage_duration_ms=self._duration_ms(stage_started_at),
                total_duration_ms=self._duration_ms(attempt_started_at),
            )
        except TransientIngestionError as exc:
            self._record_failure(
                document_version_id=document_version_id,
                code=exc.code,
                message=exc.public_message,
                attempt_id=attempt_id,
                active_stage=active_stage,
                stage_duration_ms=self._duration_ms(stage_started_at),
                total_duration_ms=self._duration_ms(attempt_started_at),
            )
            raise
        except Exception:
            self._record_failure(
                document_version_id=document_version_id,
                code="ingestion_failed",
                message="Document processing failed.",
                attempt_id=attempt_id,
                active_stage=active_stage,
                stage_duration_ms=self._duration_ms(stage_started_at),
                total_duration_ms=self._duration_ms(attempt_started_at),
            )
            raise

    @property
    def storage(self) -> ObjectStorage:
        if self._storage is None:
            self._storage = S3ObjectStorage()
        return self._storage

    @property
    def chunker(self) -> ParagraphTokenChunker:
        if self._chunker is None:
            self._chunker = ParagraphTokenChunker()
        return self._chunker

    def _lease_is_fresh(self, version: DocumentVersion) -> bool:
        lease_reference = version.updated_at or version.processing_started_at
        if lease_reference is None:
            return False
        if lease_reference.tzinfo is None:
            lease_reference = lease_reference.replace(tzinfo=UTC)

        lease_duration = timedelta(seconds=get_settings().ingestion_lease_seconds)
        return lease_reference >= datetime.now(UTC) - lease_duration

    def _start_processing(
        self,
        version: DocumentVersion,
        document: Document,
        *,
        worker_task_id: str | None,
    ) -> DocumentProcessingAttempt:
        attempted_at = datetime.now(UTC)
        previous_attempt = self.session.scalar(
            select(DocumentProcessingAttempt)
            .where(
                DocumentProcessingAttempt.document_version_id == version.id,
                DocumentProcessingAttempt.status.in_(
                    [
                        DocumentVersionStatus.EXTRACTING.value,
                        DocumentVersionStatus.CHUNKING.value,
                        DocumentVersionStatus.EMBEDDING.value,
                    ]
                ),
            )
            .order_by(DocumentProcessingAttempt.attempt_number.desc())
            .limit(1)
        )
        if previous_attempt is not None:
            previous_attempt.status = "abandoned"
            previous_attempt.completed_at = attempted_at
            previous_attempt.failure_code = "processing_lease_expired"
            previous_attempt.failure_message = (
                "The previous processing attempt did not complete."
            )
            if previous_attempt.started_at is not None:
                previous_started_at = previous_attempt.started_at
                if previous_started_at.tzinfo is None:
                    previous_started_at = previous_started_at.replace(
                        tzinfo=UTC
                    )
                previous_attempt.total_duration_ms = max(
                    0,
                    round(
                        (
                            attempted_at - previous_started_at
                        ).total_seconds()
                        * 1000
                    ),
                )

        version.status = DocumentVersionStatus.EXTRACTING
        version.processing_stage = DocumentVersionStatus.EXTRACTING
        version.attempt_count += 1
        version.last_attempted_at = attempted_at
        version.processing_started_at = attempted_at
        version.processing_completed_at = None
        version.failure_code = None
        version.failure_message = None
        attempt = DocumentProcessingAttempt(
            document_version_id=version.id,
            attempt_number=version.attempt_count,
            status=DocumentVersionStatus.EXTRACTING.value,
            worker_task_id=worker_task_id,
            started_at=attempted_at,
        )
        self.session.add(attempt)
        self._set_current_document_status(
            document,
            version,
            DocumentStatus.EXTRACTING,
        )
        self.session.commit()
        return attempt

    def _set_stage(
        self,
        version: DocumentVersion,
        document: Document,
        *,
        version_status: DocumentVersionStatus,
        document_status: DocumentStatus,
    ) -> None:
        version.status = version_status
        version.processing_stage = version_status
        self._set_current_document_status(document, version, document_status)
        self.session.commit()

    @staticmethod
    def _set_current_document_status(
        document: Document,
        version: DocumentVersion,
        status: DocumentStatus,
    ) -> None:
        if document.current_version_number == version.version_number:
            document.status = status

    def _extractor_for(self, mime_type: str) -> DocumentExtractor:
        try:
            return self.extractors[mime_type]
        except KeyError:
            raise UnsupportedDocumentTypeError(
                f"No extractor is configured for {mime_type}."
            ) from None

    @staticmethod
    def _normalize_pages(extraction: ExtractionResult) -> list[ExtractedPage]:
        normalized_pages: list[ExtractedPage] = []

        for page in extraction.pages:
            text = normalize_text(page.text)
            if text:
                normalized_pages.append(
                    ExtractedPage(
                        page_number=page.page_number,
                        text=text,
                    )
                )

        return normalized_pages

    def _record_failure(
        self,
        *,
        document_version_id: UUID,
        code: str,
        message: str,
        attempt_id: UUID | None,
        active_stage: str,
        stage_duration_ms: int,
        total_duration_ms: int,
    ) -> None:
        self.session.rollback()
        version = self.session.get(
            DocumentVersion,
            document_version_id,
            with_for_update=True,
        )
        if version is None or version.status is DocumentVersionStatus.READY:
            self.session.rollback()
            return

        document = self.session.get(Document, version.document_id)
        if document is None:
            self.session.rollback()
            return

        if attempt_id is not None:
            attempt = self.session.get(DocumentProcessingAttempt, attempt_id)
            if attempt is not None:
                attempt.status = "failed"
                attempt.completed_at = datetime.now(UTC)
                attempt.total_duration_ms = total_duration_ms
                attempt.failure_code = code[:100]
                attempt.failure_message = message[:2000]
                if active_stage == "extraction":
                    attempt.extraction_duration_ms = stage_duration_ms
                elif active_stage == "chunking":
                    attempt.chunking_duration_ms = stage_duration_ms
                elif active_stage == "embedding":
                    attempt.embedding_duration_ms = stage_duration_ms

        mark_failed(
            session=self.session,
            version=version,
            document=document,
            failure_code=code,
            public_message=message,
        )

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)


def mark_failed(
    *,
    session: Session,
    version: DocumentVersion,
    document: Document,
    failure_code: str,
    public_message: str,
) -> None:
    """Persist only stable, client-safe ingestion failure details."""
    version.status = DocumentVersionStatus.FAILED
    version.failure_code = failure_code[:100]
    version.failure_message = public_message[:2000]
    version.processing_completed_at = datetime.now(UTC)

    if document.current_version_number == version.version_number:
        document.status = DocumentStatus.FAILED

    session.commit()
