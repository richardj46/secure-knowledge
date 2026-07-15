from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from secure_knowledge_core.database.enums import OrganizationRole
from secure_knowledge_core.database.models import (
    Organization,
    OrganizationMembership,
)
from secure_knowledge_core.organizations.schemas import OrganizationCreate


class OrganizationSlugAlreadyExistsError(Exception):
    pass


class OrganizationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_organization(
        self,
        *,
        owner_user_id: UUID,
        data: OrganizationCreate,
    ) -> Organization:
        organization = Organization(
            name=data.name,
            slug=data.slug,
        )
        self.session.add(organization)

        try:
            self.session.flush()
        except IntegrityError as exc:
            # This flush only inserts the organization. Later membership
            # constraint failures remain database errors instead of being
            # mislabeled as slug conflicts.
            raise OrganizationSlugAlreadyExistsError from exc

        self.session.add(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=owner_user_id,
                role=OrganizationRole.OWNER,
            )
        )
        self.session.flush()

        return organization

    def list_for_user(self, user_id: UUID) -> list[Organization]:
        statement = (
            select(Organization)
            .join(OrganizationMembership)
            .where(OrganizationMembership.user_id == user_id)
            .order_by(Organization.created_at)
        )

        return list(self.session.scalars(statement))
