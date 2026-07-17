from datetime import datetime
from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.admin.audit import (
    AdminAuditService,
    AuditEventRead,
)
from secure_knowledge_core.admin.pagination import (
    InvalidAdminCursorError,
    Page,
)
from secure_knowledge_core.authorization.exceptions import (
    OrganizationAccessDeniedError,
)

router = APIRouter(
    prefix="/organizations/{organization_id}/admin",
    tags=["admin"],
)


def _raise_not_found(exception: Exception) -> Never:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Organization not found.",
    ) from exception


@router.get(
    "/audit-events",
    response_model=Page[AuditEventRead],
)
def list_audit_events(
    organization_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    actor_user_id: Annotated[UUID | None, Query()] = None,
    event_type: Annotated[str | None, Query(max_length=200)] = None,
    resource_type: Annotated[str | None, Query(max_length=100)] = None,
    resource_id: Annotated[UUID | None, Query()] = None,
    outcome: Annotated[str | None, Query(max_length=50)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    request_id: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> Page[AuditEventRead]:
    try:
        return AdminAuditService(session).list_events(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            filter_actor_user_id=actor_user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            date_from=date_from,
            date_to=date_to,
            request_id=request_id,
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
