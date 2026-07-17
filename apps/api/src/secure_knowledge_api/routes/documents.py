from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_api.ingestion_queue import CeleryIngestionTaskQueue
from secure_knowledge_core.database.enums import DocumentVisibility
from secure_knowledge_core.documents.schemas import (
    DocumentGroupPermissionAdd,
    DocumentGroupPermissionRead,
    DocumentRead,
    DocumentUserPermissionAdd,
    DocumentUserPermissionRead,
    DocumentVersionRead,
)
from secure_knowledge_core.documents.service import (
    DocumentNotFoundError,
    DocumentPermissionAlreadyExistsError,
    DocumentPermissionDeniedError,
    DocumentPermissionNotFoundError,
    DocumentPermissionTargetNotEligibleError,
    DocumentService,
    DocumentSlugAlreadyExistsError,
    DocumentVersionNotFoundError,
    DocumentVersionNotRetryableError,
    WorkspaceNotFoundError,
)
from secure_knowledge_core.documents.upload_service import DocumentUploadService
from secure_knowledge_core.documents.upload_validation import UploadValidationError
from secure_knowledge_core.storage.s3 import S3ObjectStorage

router = APIRouter(tags=["documents"])


@router.post(
    "/workspaces/{workspace_id}/documents/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form(min_length=1, max_length=300)],
    slug: Annotated[
        str,
        Form(
            min_length=2,
            max_length=150,
            pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        ),
    ],
    visibility: Annotated[DocumentVisibility, Form()] = (
        DocumentVisibility.WORKSPACE
    ),
) -> DocumentRead:
    try:
        document = await DocumentUploadService(
            session=session,
            storage=S3ObjectStorage(),
            task_queue=CeleryIngestionTaskQueue(),
        ).upload(
            workspace_id=workspace_id,
            user_id=current_user.id,
            title=title,
            slug=slug,
            visibility=visibility,
            upload_file=file,
        )
    except UploadValidationError as exc:
        error_status = (
            status.HTTP_413_CONTENT_TOO_LARGE
            if str(exc) == "File is too large."
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(error_status, str(exc)) from exc
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found.") from exc
    except DocumentPermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc
    except DocumentSlugAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Document slug already exists in this workspace.",
        ) from exc
    finally:
        await file.close()

    return DocumentRead.model_validate(document)


@router.get(
    "/workspaces/{workspace_id}/documents",
    response_model=list[DocumentRead],
)
def list_documents(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[DocumentRead]:
    try:
        documents = DocumentService(session).list_documents(
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found.") from exc

    return [DocumentRead.model_validate(document) for document in documents]


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> DocumentRead:
    try:
        document = DocumentService(session).get_document(
            document_id=document_id,
            actor_user_id=current_user.id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc

    return DocumentRead.model_validate(document)


@router.get(
    "/documents/{document_id}/versions",
    response_model=list[DocumentVersionRead],
)
def list_document_versions(
    document_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[DocumentVersionRead]:
    try:
        versions = DocumentService(session).list_document_versions(
            document_id=document_id,
            actor_user_id=current_user.id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc

    return [DocumentVersionRead.model_validate(version) for version in versions]


@router.get(
    "/document-versions/{version_id}",
    response_model=DocumentVersionRead,
)
def get_document_version(
    version_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> DocumentVersionRead:
    try:
        version = DocumentService(session).get_document_version(
            version_id=version_id,
            actor_user_id=current_user.id,
        )
    except DocumentVersionNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Document version not found.",
        ) from exc

    return DocumentVersionRead.model_validate(version)


@router.post(
    "/document-versions/{version_id}/retry",
    response_model=DocumentVersionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_document_version(
    version_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> DocumentVersionRead:
    try:
        version = DocumentService(session).retry_document_version(
            version_id=version_id,
            actor_user_id=current_user.id,
        )
    except (DocumentNotFoundError, DocumentVersionNotFoundError) as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Document version not found.",
        ) from exc
    except DocumentPermissionDeniedError as exc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Insufficient permissions.",
        ) from exc
    except DocumentVersionNotRetryableError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only failed document versions can be retried.",
        ) from exc

    return DocumentVersionRead.model_validate(version)


@router.post(
    "/documents/{document_id}/permissions/users",
    response_model=DocumentUserPermissionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_user_permission(
    document_id: UUID,
    data: DocumentUserPermissionAdd,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> DocumentUserPermissionRead:
    try:
        permission = DocumentService(session).add_user_permission(
            document_id=document_id,
            actor_user_id=current_user.id,
            data=data,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except (
        DocumentPermissionDeniedError,
        DocumentPermissionTargetNotEligibleError,
    ) as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc
    except DocumentPermissionAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Permission already exists.") from exc

    return DocumentUserPermissionRead.model_validate(permission)


@router.post(
    "/documents/{document_id}/permissions/groups",
    response_model=DocumentGroupPermissionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_group_permission(
    document_id: UUID,
    data: DocumentGroupPermissionAdd,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> DocumentGroupPermissionRead:
    try:
        permission = DocumentService(session).add_group_permission(
            document_id=document_id,
            actor_user_id=current_user.id,
            data=data,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except (
        DocumentPermissionDeniedError,
        DocumentPermissionTargetNotEligibleError,
    ) as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc
    except DocumentPermissionAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Permission already exists.") from exc

    return DocumentGroupPermissionRead.model_validate(permission)


@router.delete(
    "/documents/{document_id}/permissions/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_user_permission(
    document_id: UUID,
    user_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> Response:
    try:
        DocumentService(session).remove_user_permission(
            document_id=document_id,
            actor_user_id=current_user.id,
            user_id=user_id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except DocumentPermissionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Permission not found.") from exc
    except DocumentPermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/documents/{document_id}/permissions/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_group_permission(
    document_id: UUID,
    group_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> Response:
    try:
        DocumentService(session).remove_group_permission(
            document_id=document_id,
            actor_user_id=current_user.id,
            group_id=group_id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.") from exc
    except DocumentPermissionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Permission not found.") from exc
    except DocumentPermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
