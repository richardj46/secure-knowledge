from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.database.enums import (
    DocumentStatus,
    DocumentVersionStatus,
)
from secure_knowledge_core.database.models import (
    Document,
    DocumentChunk,
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

    def ingest(self, *, document_version_id: UUID) -> None:
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

        try:
            self._start_processing(version, document)
            try:
                content = self.storage.download(key=version.storage_key)
            except Exception:
                raise StorageDownloadError from None
            extractor = self._extractor_for(document.mime_type)
            extraction = extractor.extract(content)
            normalized_pages = self._normalize_pages(extraction)
            normalized_extraction = ExtractionResult(pages=normalized_pages)
            total_text = normalized_extraction.full_text
            if len(total_text) < 20:
                raise NoExtractableTextError(
                    "The document contains too little extractable text."
                )

            self._set_stage(
                version,
                document,
                version_status=DocumentVersionStatus.CHUNKING,
                document_status=DocumentStatus.CHUNKING,
            )
            chunks = self.chunker.chunk(normalized_extraction)
            if not chunks:
                raise NoChunksGeneratedError(
                    "The document produced no non-empty chunks."
                )

            self._set_stage(
                version,
                document,
                version_status=DocumentVersionStatus.EMBEDDING,
                document_status=DocumentStatus.EMBEDDING,
            )
            embeddings = self.embedding_provider.embed_texts(
                [chunk.content for chunk in chunks]
            )
            if len(embeddings) != len(chunks):
                raise EmbeddingCountMismatchError(
                    "The embedding count does not match the chunk count."
                )

            # The previous stage commit ended its transaction. This delete,
            # all inserts, and the READY transition share one final transaction.
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
                    for chunk, embedding in zip(chunks, embeddings, strict=True)
                ]
            )

            version.status = DocumentVersionStatus.READY
            version.page_count = len(extraction.pages)
            version.extracted_character_count = len(total_text)
            version.chunk_count = len(chunks)
            version.processing_completed_at = datetime.now(UTC)
            version.failure_code = None
            version.failure_message = None
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
            )
        except TransientIngestionError as exc:
            self._record_failure(
                document_version_id=document_version_id,
                code=exc.code,
                message=exc.public_message,
            )
            raise
        except Exception:
            self._record_failure(
                document_version_id=document_version_id,
                code="ingestion_failed",
                message="Document processing failed.",
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
    ) -> None:
        version.status = DocumentVersionStatus.EXTRACTING
        version.processing_started_at = datetime.now(UTC)
        version.processing_completed_at = None
        version.failure_code = None
        version.failure_message = None
        self._set_current_document_status(
            document,
            version,
            DocumentStatus.EXTRACTING,
        )
        self.session.commit()

    def _set_stage(
        self,
        version: DocumentVersion,
        document: Document,
        *,
        version_status: DocumentVersionStatus,
        document_status: DocumentStatus,
    ) -> None:
        version.status = version_status
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

        mark_failed(
            session=self.session,
            version=version,
            document=document,
            failure_code=code,
            public_message=message,
        )


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
