from uuid import UUID

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from secure_knowledge_core.database.enums import (
    DocumentVisibility,
    OrganizationRole,
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

    return and_(
        Document.organization_id == organization_id,
        organization_member,
        or_(
            organization_admin,
            organization_visible,
            workspace_visible,
            document_owner,
            direct_user_permission,
            group_permission,
        ),
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
