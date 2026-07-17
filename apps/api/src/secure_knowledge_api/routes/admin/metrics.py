from datetime import datetime
from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.admin.metrics import (
    AdminMetricsDateRangeError,
    AdminMetricsService,
    AdminMetricsWorkspaceNotFoundError,
    AdminOverviewMetrics,
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
        detail="Organization or workspace not found.",
    ) from exception


@router.get(
    "/metrics/overview",
    response_model=AdminOverviewMetrics,
)
def get_metrics_overview(
    organization_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    workspace_id: Annotated[UUID | None, Query()] = None,
) -> AdminOverviewMetrics:
    try:
        return AdminMetricsService(session).overview(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            date_from=date_from,
            date_to=date_to,
            workspace_id=workspace_id,
        )
    except (
        AdminMetricsWorkspaceNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)
    except AdminMetricsDateRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
