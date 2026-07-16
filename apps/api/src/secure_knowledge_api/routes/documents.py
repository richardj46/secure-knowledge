from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from secure_knowledge_core.documents.schemas import (
    DocumentCreate,
    DocumentGroupPermissionAdd,
    DocumentGroupPermissionRead,
    DocumentRead,
    DocumentUserPermissionAdd,
    DocumentUserPermissionRead,
)
from secure_knowledge_core.documents.service import (
    DocumentNotFoundError,
    DocumentPermissionAlreadyExistsError,
    DocumentPermissionDeniedError,
    DocumentPermissionNotFoundError,
    DocumentPermissionTargetNotEligibleError,
    DocumentService,
    DocumentSlugAlreadyExistsError,
    WorkspaceNotFoundError,
)

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession

router = APIRouter(tags=["documents"])


@router.post(
    "/workspaces/{workspace_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    workspace_id: UUID,
    data: DocumentCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> DocumentRead:
    try:
        document = DocumentService(session).create_document(
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
            data=data,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found.") from exc
    except DocumentPermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc
    except DocumentSlugAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Document slug already exists in this workspace.",
        ) from exc

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
