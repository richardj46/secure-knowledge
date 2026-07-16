from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from secure_knowledge_core.authorization.exceptions import (
    OrganizationAccessDeniedError,
)
from secure_knowledge_core.database.enums import OrganizationRole
from secure_knowledge_core.database.models import OrganizationMembership


class AuthorizationService:
    _admin_roles = {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    def require_organization_membership(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationMembership:
        membership = self.session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        if membership is None:
            raise OrganizationAccessDeniedError
        return membership

    def require_admin_access(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationMembership:
        membership = self.require_organization_membership(
            organization_id=organization_id,
            user_id=user_id,
        )
        if membership.role not in self._admin_roles:
            raise OrganizationAccessDeniedError
        return membership
