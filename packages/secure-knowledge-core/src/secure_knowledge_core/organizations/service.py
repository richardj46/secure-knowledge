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
        try:
            with self.session.begin():
                organization = Organization(
                    name=data.name,
                    slug=data.slug,
                )
                self.session.add(organization)
                self.session.flush()

                self.session.add(
                    OrganizationMembership(
                        organization_id=organization.id,
                        user_id=owner_user_id,
                        role=OrganizationRole.OWNER,
                    )
                )
        except IntegrityError as exc:
            raise OrganizationSlugAlreadyExistsError from exc

        return organization

    def list_for_user(self, user_id: UUID) -> list[Organization]:
        statement = (
            select(Organization)
            .join(OrganizationMembership)
            .where(OrganizationMembership.user_id == user_id)
            .order_by(Organization.created_at)
        )

        return list(self.session.scalars(statement))