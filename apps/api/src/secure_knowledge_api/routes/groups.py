from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.groups.schemas import (
    GroupCreate,
    GroupMemberAdd,
    GroupMembershipRead,
    GroupRead,
)
from secure_knowledge_core.groups.service import (
    GroupMemberNotEligibleError,
    GroupMembershipAlreadyExistsError,
    GroupMembershipNotFoundError,
    GroupNameAlreadyExistsError,
    GroupNotFoundError,
    GroupPermissionDeniedError,
    GroupService,
    OrganizationNotFoundError,
)

router = APIRouter(tags=["groups"])


@router.post(
    "/organizations/{organization_id}/groups",
    response_model=GroupRead,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    organization_id: UUID,
    data: GroupCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> GroupRead:
    try:
        group = GroupService(session).create_group(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            data=data,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found.") from exc
    except GroupPermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc
    except GroupNameAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Group name already exists in this organization.",
        ) from exc

    return GroupRead.model_validate(group)


@router.get(
    "/organizations/{organization_id}/groups",
    response_model=list[GroupRead],
)
def list_groups(
    organization_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[GroupRead]:
    try:
        groups = GroupService(session).list_groups(
            organization_id=organization_id,
            actor_user_id=current_user.id,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found.") from exc

    return [GroupRead.model_validate(group) for group in groups]


@router.post(
    "/groups/{group_id}/members",
    response_model=GroupMembershipRead,
    status_code=status.HTTP_201_CREATED,
)
def add_group_member(
    group_id: UUID,
    data: GroupMemberAdd,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> GroupMembershipRead:
    try:
        membership = GroupService(session).add_member(
            group_id=group_id,
            actor_user_id=current_user.id,
            user_id=data.user_id,
        )
    except GroupNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found.") from exc
    except (GroupPermissionDeniedError, GroupMemberNotEligibleError) as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc
    except GroupMembershipAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "User is already a group member.",
        ) from exc

    return GroupMembershipRead.model_validate(membership)


@router.delete(
    "/groups/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_group_member(
    group_id: UUID,
    user_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> Response:
    try:
        GroupService(session).remove_member(
            group_id=group_id,
            actor_user_id=current_user.id,
            user_id=user_id,
        )
    except (GroupNotFoundError, GroupMembershipNotFoundError) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group membership not found.") from exc
    except GroupPermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.") from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
