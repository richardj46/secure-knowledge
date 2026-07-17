from datetime import datetime
from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.admin.documents import (
    AdminDocumentService,
    AdminDocumentVersionNotFoundError,
    AdminDocumentVersionNotRetryableError,
    FailedDocumentVersionDetail,
    FailedDocumentVersionSummary,
)
from secure_knowledge_core.admin.pagination import (
    InvalidAdminCursorError,
    Page,
)
from secure_knowledge_core.authorization.exceptions import (
    OrganizationAccessDeniedError,
)
from secure_knowledge_core.core.logging import request_id_context

router = APIRouter(
    prefix="/organizations/{organization_id}/admin",
    tags=["admin"],
)


def _raise_not_found(exception: Exception) -> Never:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Document version not found.",
    ) from exception


@router.get(
    "/document-versions/failed",
    response_model=Page[FailedDocumentVersionSummary],
)
def list_failed_document_versions(
    organization_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    failure_code: Annotated[str | None, Query(max_length=100)] = None,
    mime_type: Annotated[str | None, Query(max_length=150)] = None,
    workspace_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    retry_count: Annotated[int | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> Page[FailedDocumentVersionSummary]:
    try:
        return AdminDocumentService(session).list_failed_versions(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            failure_code=failure_code,
            mime_type=mime_type,
            workspace_id=workspace_id,
            date_from=date_from,
            date_to=date_to,
            retry_count=retry_count,
            limit=limit,
            cursor=cursor,
        )
    except OrganizationAccessDeniedError as exc:
        _raise_not_found(exc)
    except InvalidAdminCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid pagination cursor.",
        ) from exc


@router.get(
    "/document-versions/{version_id}",
    response_model=FailedDocumentVersionDetail,
)
def get_admin_document_version(
    organization_id: UUID,
    version_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> FailedDocumentVersionDetail:
    try:
        return AdminDocumentService(session).get_version(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            version_id=version_id,
        )
    except (
        AdminDocumentVersionNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)


@router.post(
    "/document-versions/{version_id}/retry",
    response_model=FailedDocumentVersionDetail,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_admin_document_version(
    organization_id: UUID,
    version_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> FailedDocumentVersionDetail:
    try:
        return AdminDocumentService(session).retry_version(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            version_id=version_id,
            request_id=request_id_context.get(),
        )
    except (
        AdminDocumentVersionNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)
    except AdminDocumentVersionNotRetryableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed document versions can be retried.",
        ) from exc
