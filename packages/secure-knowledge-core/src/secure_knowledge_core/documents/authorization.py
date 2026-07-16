from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from secure_knowledge_core.database.enums import OrganizationRole, WorkspaceRole
from secure_knowledge_core.database.models import (
    OrganizationMembership,
    Workspace,
    WorkspaceMembership,
)
from secure_knowledge_core.documents.service import DocumentPermissionDeniedError


class AuthorizationService:
    _organization_managers = {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    def require_document_creation(
        self,
        *,
        workspace: Workspace,
        user_id: UUID,
    ) -> None:
        organization_role = self.session.scalar(
            select(OrganizationMembership.role).where(
                OrganizationMembership.organization_id == workspace.organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        if organization_role in self._organization_managers:
            return

        workspace_role = self.session.scalar(
            select(WorkspaceMembership.role).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.user_id == user_id,
            )
        )
        if workspace_role is WorkspaceRole.MANAGER:
            return

        raise DocumentPermissionDeniedError
