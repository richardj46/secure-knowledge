from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.workspaces.schemas import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMembershipRead,
    WorkspaceRead,
)
from secure_knowledge_core.workspaces.service import (
    OrganizationNotFoundError,
    WorkspaceMemberNotEligibleError,
    WorkspaceMembershipAlreadyExistsError,
    WorkspaceNotFoundError,
    WorkspacePermissionDeniedError,
    WorkspaceService,
    WorkspaceSlugAlreadyExistsError,
)

router = APIRouter(tags=["workspaces"])


@router.post(
    "/organizations/{organization_id}/workspaces",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    organization_id: UUID,
    data: WorkspaceCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkspaceRead:
    service = WorkspaceService(session)

    try:
        workspace = service.create_workspace(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            data=data,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found.") from exc
    except WorkspacePermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc
    except WorkspaceSlugAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Workspace slug already exists in this organization.",
        ) from exc

    return WorkspaceRead.model_validate(workspace)


@router.get(
    "/organizations/{organization_id}/workspaces",
    response_model=list[WorkspaceRead],
)
def list_workspaces(
    organization_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[WorkspaceRead]:
    try:
        workspaces = WorkspaceService(session).list_workspaces(
            organization_id=organization_id,
            actor_user_id=current_user.id,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found.") from exc

    return [WorkspaceRead.model_validate(workspace) for workspace in workspaces]


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceRead,
)
def get_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkspaceRead:
    try:
        workspace = WorkspaceService(session).get_workspace(
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found.") from exc

    return WorkspaceRead.model_validate(workspace)


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=WorkspaceMembershipRead,
    status_code=status.HTTP_201_CREATED,
)
def add_workspace_member(
    workspace_id: UUID,
    data: WorkspaceMemberCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> WorkspaceMembershipRead:
    service = WorkspaceService(session)

    try:
        membership = service.add_member(
            workspace_id=workspace_id,
            actor_user_id=current_user.id,
            data=data,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found.") from exc
    except (WorkspacePermissionDeniedError, WorkspaceMemberNotEligibleError) as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc
    except WorkspaceMembershipAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "User is already a workspace member.",
        ) from exc

    return WorkspaceMembershipRead.model_validate(membership)
