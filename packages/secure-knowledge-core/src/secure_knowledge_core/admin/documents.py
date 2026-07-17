from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from secure_knowledge_core.admin.pagination import (
    Page,
    decode_datetime_cursor,
    encode_datetime_cursor,
)
from secure_knowledge_core.audit.events import AuditEventType
from secure_knowledge_core.audit.service import AuditService
from secure_knowledge_core.authorization.service import AuthorizationService
from secure_knowledge_core.database.enums import (
    DocumentStatus,
    DocumentVersionStatus,
)
from secure_knowledge_core.database.models import (
    Document,
    DocumentProcessingAttempt,
    DocumentVersion,
    OutboxEvent,
)
from secure_knowledge_core.outbox.service import (
    DOCUMENT_VERSION_INGESTION_REQUESTED,
)


class AdminDocumentVersionNotFoundError(Exception):
    """Raised when an admin-visible document version cannot be found."""


class AdminDocumentVersionNotRetryableError(Exception):
    """Raised when a document version is not currently failed."""


class FailedDocumentVersionSummary(BaseModel):
    document_id: UUID
    document_title: str
    document_status: DocumentStatus
    workspace_id: UUID
    version_id: UUID
    version_number: int
    filename: str
    mime_type: str
    file_size_bytes: int
    checksum: str
    status: DocumentVersionStatus
    processing_stage: DocumentVersionStatus | None
    failure_code: str | None
    safe_failure_message: str | None
    attempt_count: int
    retry_count: int
    last_attempted_at: datetime | None
    created_at: datetime
    completed_at: datetime | None


class DocumentProcessingAttemptRead(BaseModel):
    id: UUID
    attempt_number: int
    status: str
    worker_task_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    extraction_duration_ms: int | None
    chunking_duration_ms: int | None
    embedding_duration_ms: int | None
    total_duration_ms: int | None
    extracted_character_count: int | None
    chunk_count: int | None
    failure_code: str | None
    safe_failure_message: str | None


class FailedDocumentVersionDetail(FailedDocumentVersionSummary):
    processing_attempts: list[DocumentProcessingAttemptRead]


_SAFE_FAILURE_MESSAGES = {
    "corrupted_document": "The document is corrupted or cannot be read.",
    "embedding_not_configured": "The embedding service is not configured.",
    "embedding_provider_error": (
        "The embedding service could not process the document."
    ),
    "encrypted_pdf": "Encrypted PDF documents are not supported.",
    "ingestion_failed": "Document processing failed.",
    "no_chunks_generated": (
        "The document contains no content that can be indexed."
    ),
    "no_extractable_text": "The document contains no extractable text.",
    "ocr_required": (
        "The document contains no extractable text and may require OCR."
    ),
    "permanent_ingestion_error": "Document processing failed.",
    "processing_lease_expired": (
        "The previous processing attempt did not complete."
    ),
    "storage_download_failed": "The stored document could not be retrieved.",
    "unsupported_file_type": "The document file type is not supported.",
    "unsupported_text_encoding": (
        "Plain-text documents must use UTF-8 encoding."
    ),
}


class AdminDocumentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.authorization = AuthorizationService(session)
        self.audit = AuditService(session)

    def list_failed_versions(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        failure_code: str | None,
        mime_type: str | None,
        workspace_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        retry_count: int | None,
        limit: int,
        cursor: str | None,
    ) -> Page[FailedDocumentVersionSummary]:
        self._require_admin(organization_id, actor_user_id)
        statement = (
            select(DocumentVersion, Document)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(
                Document.organization_id == organization_id,
                DocumentVersion.status == DocumentVersionStatus.FAILED,
            )
        )
        if failure_code is not None:
            statement = statement.where(
                DocumentVersion.failure_code == failure_code
            )
        if mime_type is not None:
            statement = statement.where(Document.mime_type == mime_type)
        if workspace_id is not None:
            statement = statement.where(Document.workspace_id == workspace_id)
        if date_from is not None:
            statement = statement.where(DocumentVersion.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(DocumentVersion.created_at <= date_to)
        if retry_count is not None:
            statement = statement.where(
                DocumentVersion.retry_count == retry_count
            )
        if cursor is not None:
            cursor_time, cursor_id = decode_datetime_cursor(cursor)
            statement = statement.where(
                or_(
                    DocumentVersion.created_at < cursor_time,
                    and_(
                        DocumentVersion.created_at == cursor_time,
                        DocumentVersion.id < cursor_id,
                    ),
                )
            )

        rows = self.session.execute(
            statement.order_by(
                DocumentVersion.created_at.desc(),
                DocumentVersion.id.desc(),
            )
            .limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [
            self._to_summary(version, document)
            for version, document in rows
        ]
        next_cursor = (
            encode_datetime_cursor(rows[-1][0].created_at, rows[-1][0].id)
            if has_more and rows
            else None
        )
        return Page(items=items, next_cursor=next_cursor)

    def get_version(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        version_id: UUID,
    ) -> FailedDocumentVersionDetail:
        self._require_admin(organization_id, actor_user_id)
        version, document = self._get_version_row(
            organization_id=organization_id,
            version_id=version_id,
        )
        return self._to_detail(version, document)

    def retry_version(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        version_id: UUID,
        request_id: str | None,
    ) -> FailedDocumentVersionDetail:
        self._require_admin(organization_id, actor_user_id)
        row = self.session.execute(
            select(DocumentVersion, Document)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(
                DocumentVersion.id == version_id,
                Document.organization_id == organization_id,
            )
            .with_for_update(of=DocumentVersion)
        ).one_or_none()
        if row is None:
            raise AdminDocumentVersionNotFoundError

        version, document = row
        if version.status is not DocumentVersionStatus.FAILED:
            raise AdminDocumentVersionNotRetryableError

        previous_failure_code = version.failure_code
        version.status = DocumentVersionStatus.QUEUED
        version.processing_stage = DocumentVersionStatus.QUEUED
        version.retry_count += 1
        version.failure_code = None
        version.failure_message = None
        version.processing_started_at = None
        version.processing_completed_at = None
        version.page_count = None
        version.extracted_character_count = None
        version.chunk_count = None
        if document.current_version_number == version.version_number:
            document.status = DocumentStatus.QUEUED

        self.session.add(
            OutboxEvent(
                event_type=DOCUMENT_VERSION_INGESTION_REQUESTED,
                aggregate_type="document_version",
                aggregate_id=version.id,
                payload={"document_version_id": str(version.id)},
            )
        )
        self.audit.record(
            organization_id=organization_id,
            event_type=AuditEventType.DOCUMENT_INGESTION_RETRIED,
            resource_type="document_version",
            resource_id=version.id,
            actor_user_id=actor_user_id,
            outcome="succeeded",
            request_id=request_id,
            details={
                "document_id": str(document.id),
                "previous_failure_code": previous_failure_code,
                "retry_count": version.retry_count,
            },
        )
        self.session.commit()
        self.session.refresh(version)
        self.session.refresh(document)
        return self._to_detail(version, document)

    def _get_version_row(
        self,
        *,
        organization_id: UUID,
        version_id: UUID,
    ) -> tuple[DocumentVersion, Document]:
        row = self.session.execute(
            select(DocumentVersion, Document)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(
                DocumentVersion.id == version_id,
                Document.organization_id == organization_id,
            )
        ).one_or_none()
        if row is None:
            raise AdminDocumentVersionNotFoundError
        version, document = row
        return version, document

    @staticmethod
    def _to_summary(
        version: DocumentVersion,
        document: Document,
    ) -> FailedDocumentVersionSummary:
        failure_message = (
            _SAFE_FAILURE_MESSAGES.get(
                version.failure_code,
                "Document processing failed.",
            )
            if version.failure_code is not None
            else None
        )
        return FailedDocumentVersionSummary(
            document_id=document.id,
            document_title=document.title,
            document_status=document.status,
            workspace_id=document.workspace_id,
            version_id=version.id,
            version_number=version.version_number,
            filename=document.source_filename,
            mime_type=document.mime_type,
            file_size_bytes=version.file_size_bytes,
            checksum=version.checksum,
            status=version.status,
            processing_stage=version.processing_stage,
            failure_code=version.failure_code,
            safe_failure_message=failure_message,
            attempt_count=version.attempt_count,
            retry_count=version.retry_count,
            last_attempted_at=version.last_attempted_at,
            created_at=version.created_at,
            completed_at=version.processing_completed_at,
        )

    def _to_detail(
        self,
        version: DocumentVersion,
        document: Document,
    ) -> FailedDocumentVersionDetail:
        summary = self._to_summary(version, document)
        attempts = self.session.scalars(
            select(DocumentProcessingAttempt)
            .where(
                DocumentProcessingAttempt.document_version_id == version.id
            )
            .order_by(DocumentProcessingAttempt.attempt_number)
        ).all()
        return FailedDocumentVersionDetail(
            **summary.model_dump(),
            processing_attempts=[
                DocumentProcessingAttemptRead(
                    id=attempt.id,
                    attempt_number=attempt.attempt_number,
                    status=attempt.status,
                    worker_task_id=attempt.worker_task_id,
                    started_at=attempt.started_at,
                    completed_at=attempt.completed_at,
                    extraction_duration_ms=attempt.extraction_duration_ms,
                    chunking_duration_ms=attempt.chunking_duration_ms,
                    embedding_duration_ms=attempt.embedding_duration_ms,
                    total_duration_ms=attempt.total_duration_ms,
                    extracted_character_count=(
                        attempt.extracted_character_count
                    ),
                    chunk_count=attempt.chunk_count,
                    failure_code=attempt.failure_code,
                    safe_failure_message=(
                        _SAFE_FAILURE_MESSAGES.get(
                            attempt.failure_code,
                            "Document processing failed.",
                        )
                        if attempt.failure_code is not None
                        else None
                    ),
                )
                for attempt in attempts
            ],
        )

    def _require_admin(
        self,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        self.authorization.require_admin_access(
            organization_id=organization_id,
            user_id=actor_user_id,
        )
