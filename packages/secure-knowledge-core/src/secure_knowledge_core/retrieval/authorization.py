from uuid import UUID

from sqlalchemy import String, Uuid, and_, case, cast, exists, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from secure_knowledge_core.database.enums import (
    DocumentVisibility,
    OrganizationRole,
    PermissionPath,
)
from secure_knowledge_core.database.models import (
    Document,
    DocumentGroupPermission,
    DocumentUserPermission,
    GroupMembership,
    OrganizationMembership,
    WorkspaceMembership,
)
from secure_knowledge_core.retrieval.exceptions import OrganizationNotFoundError


def build_authorized_document_condition(
    *,
    user_id: UUID,
    organization_id: UUID,
) -> ColumnElement[bool]:
    paths = build_document_permission_paths(
        user_id=user_id,
        organization_id=organization_id,
    )

    return and_(
        Document.organization_id == organization_id,
        paths["organization_member"],
        or_(
            paths["organization_admin"],
            paths["organization_visibility"],
            paths["workspace_membership"],
            paths["document_owner"],
            paths["direct_user_grant"],
            paths["group_grant"],
        ),
    )


def build_document_permission_paths(
    *,
    user_id: UUID,
    organization_id: UUID,
) -> dict[str, ColumnElement[bool]]:
    organization_member = exists(
        select(1).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
    )

    organization_admin = exists(
        select(1).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.role.in_(
                [
                    OrganizationRole.OWNER,
                    OrganizationRole.ADMIN,
                ]
            ),
        )
    )

    organization_visible = Document.visibility == DocumentVisibility.ORGANIZATION

    workspace_visible = and_(
        Document.visibility == DocumentVisibility.WORKSPACE,
        exists(
            select(1).where(
                WorkspaceMembership.workspace_id == Document.workspace_id,
                WorkspaceMembership.user_id == user_id,
            )
        ),
    )

    document_owner = Document.owner_user_id == user_id

    direct_user_permission = exists(
        select(1).where(
            DocumentUserPermission.document_id == Document.id,
            DocumentUserPermission.user_id == user_id,
        )
    )

    group_permission = exists(
        select(1)
        .select_from(DocumentGroupPermission)
        .join(
            GroupMembership,
            GroupMembership.group_id == DocumentGroupPermission.group_id,
        )
        .where(
            DocumentGroupPermission.document_id == Document.id,
            GroupMembership.user_id == user_id,
        )
    )

    return {
        "organization_member": organization_member,
        "organization_admin": organization_admin,
        "organization_visibility": organization_visible,
        "workspace_membership": workspace_visible,
        "document_owner": document_owner,
        "direct_user_grant": direct_user_permission,
        "group_grant": group_permission,
    }


def build_document_permission_path_expression(
    *,
    user_id: UUID,
    organization_id: UUID,
) -> ColumnElement[str]:
    paths = build_document_permission_paths(
        user_id=user_id,
        organization_id=organization_id,
    )
    return cast(
        case(
            (
                paths["organization_admin"],
                PermissionPath.ORGANIZATION_ADMIN.value,
            ),
            (paths["document_owner"], PermissionPath.DOCUMENT_OWNER.value),
            (
                paths["organization_visibility"],
                PermissionPath.ORGANIZATION_VISIBILITY.value,
            ),
            (
                paths["workspace_membership"],
                PermissionPath.WORKSPACE_MEMBERSHIP.value,
            ),
            (
                paths["direct_user_grant"],
                PermissionPath.DIRECT_USER_GRANT.value,
            ),
            (paths["group_grant"], PermissionPath.GROUP_GRANT.value),
            else_="unknown",
        ),
        String,
    )


def build_document_permission_source_id_expression(
    *,
    user_id: UUID,
    organization_id: UUID,
) -> ColumnElement[UUID]:
    paths = build_document_permission_paths(
        user_id=user_id,
        organization_id=organization_id,
    )
    organization_membership_id = (
        select(OrganizationMembership.id)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
        .limit(1)
        .scalar_subquery()
    )
    workspace_membership_id = (
        select(WorkspaceMembership.id)
        .where(
            WorkspaceMembership.workspace_id == Document.workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        .limit(1)
        .scalar_subquery()
    )
    direct_permission_id = (
        select(DocumentUserPermission.id)
        .where(
            DocumentUserPermission.document_id == Document.id,
            DocumentUserPermission.user_id == user_id,
        )
        .limit(1)
        .scalar_subquery()
    )
    group_id = (
        select(DocumentGroupPermission.group_id)
        .join(
            GroupMembership,
            GroupMembership.group_id == DocumentGroupPermission.group_id,
        )
        .where(
            DocumentGroupPermission.document_id == Document.id,
            GroupMembership.user_id == user_id,
        )
        .order_by(DocumentGroupPermission.group_id)
        .limit(1)
        .scalar_subquery()
    )
    return cast(
        case(
            (paths["organization_admin"], organization_membership_id),
            (paths["document_owner"], Document.owner_user_id),
            (paths["organization_visibility"], Document.organization_id),
            (paths["workspace_membership"], workspace_membership_id),
            (paths["direct_user_grant"], direct_permission_id),
            (paths["group_grant"], group_id),
            else_=None,
        ),
        Uuid,
    )


class RetrievalAuthorization:
    def __init__(self, session: Session) -> None:
        self.session = session

    def require_organization_membership(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        membership_id = self.session.scalar(
            select(OrganizationMembership.id).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == actor_user_id,
            )
        )
        if membership_id is None:
            raise OrganizationNotFoundError
