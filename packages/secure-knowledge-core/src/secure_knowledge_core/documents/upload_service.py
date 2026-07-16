from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from secure_knowledge_core.core.settings import get_settings
from secure_knowledge_core.database.enums import (
    DocumentStatus,
    DocumentVersionStatus,
    DocumentVisibility,
)
from secure_knowledge_core.database.models import (
    Document,
    DocumentVersion,
    OutboxEvent,
    Workspace,
)
from secure_knowledge_core.documents.authorization import AuthorizationService
from secure_knowledge_core.documents.service import (
    DocumentSlugAlreadyExistsError,
    WorkspaceNotFoundError,
)
from secure_knowledge_core.documents.storage_keys import build_storage_key
from secure_knowledge_core.documents.upload_validation import (
    AsyncUploadReader,
    buffer_upload,
    validate_file_signature,
    validate_upload_metadata,
)
from secure_knowledge_core.ingestion.queue import IngestionTaskQueue
from secure_knowledge_core.outbox.service import (
    DOCUMENT_VERSION_INGESTION_REQUESTED,
    OutboxPublisher,
)
from secure_knowledge_core.storage.interface import ObjectStorage


class DocumentUploadService:
    def __init__(
        self,
        *,
        session: Session,
        storage: ObjectStorage,
        task_queue: IngestionTaskQueue,
    ) -> None:
        self.session = session
        self.storage = storage
        self.task_queue = task_queue
        self.authorization = AuthorizationService(session)

    async def upload(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        title: str,
        slug: str,
        visibility: DocumentVisibility,
        upload_file: AsyncUploadReader,
    ) -> Document:
        workspace = self.session.get(Workspace, workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError

        self.authorization.require_document_creation(
            workspace=workspace,
            user_id=user_id,
        )

        validated = validate_upload_metadata(
            filename=upload_file.filename,
            content_type=upload_file.content_type,
        )
        buffered = await buffer_upload(
            upload_file,
            maximum_size=get_settings().max_upload_size_bytes,
        )

        try:
            validate_file_signature(
                file_object=buffered.file_object,
                content_type=validated.content_type,
            )

            document = Document(
                id=uuid4(),
                organization_id=workspace.organization_id,
                workspace_id=workspace.id,
                owner_user_id=user_id,
                title=title,
                slug=slug,
                source_filename=validated.filename,
                mime_type=validated.content_type,
                storage_key="pending",
                visibility=visibility,
                status=DocumentStatus.PENDING,
                current_version_number=1,
            )
            version = DocumentVersion(
                id=uuid4(),
                document_id=document.id,
                version_number=1,
                storage_key="pending",
                checksum=buffered.checksum,
                file_size_bytes=buffered.size_bytes,
                status=DocumentVersionStatus.PENDING,
            )
            storage_key = build_storage_key(
                organization_id=workspace.organization_id,
                document_id=document.id,
                version_id=version.id,
            )
            document.storage_key = storage_key
            version.storage_key = storage_key
            outbox_event = OutboxEvent(
                event_type=DOCUMENT_VERSION_INGESTION_REQUESTED,
                aggregate_type="document_version",
                aggregate_id=version.id,
                payload={
                    "document_version_id": str(version.id),
                },
            )

            try:
                self.storage.upload(
                    file_object=buffered.file_object,
                    key=storage_key,
                    content_type=validated.content_type,
                )
                document.status = DocumentStatus.STORED
                self.session.add_all([document, version, outbox_event])
                self.session.commit()
            except IntegrityError as exc:
                self.session.rollback()
                self._delete_after_failed_upload(storage_key)
                raise DocumentSlugAlreadyExistsError from exc
            except Exception:
                self.session.rollback()
                self._delete_after_failed_upload(storage_key)
                raise
        finally:
            buffered.file_object.close()

        OutboxPublisher(
            session=self.session,
            task_queue=self.task_queue,
        ).publish_event(event_id=outbox_event.id)
        self.session.refresh(document)
        return document

    def _delete_after_failed_upload(self, storage_key: str) -> None:
        try:
            self.storage.delete(key=storage_key)
        except Exception:
            # Cleanup is best-effort; callers must receive the original failure.
            pass
