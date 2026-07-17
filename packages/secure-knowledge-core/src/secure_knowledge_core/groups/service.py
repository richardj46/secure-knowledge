from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from secure_knowledge_core.database.enums import OrganizationRole
from secure_knowledge_core.database.models import (
    Group,
    GroupMembership,
    OrganizationMembership,
)
from secure_knowledge_core.groups.schemas import GroupCreate


class OrganizationNotFoundError(Exception):
    pass


class GroupNotFoundError(Exception):
    pass


class GroupPermissionDeniedError(Exception):
    pass


class GroupNameAlreadyExistsError(Exception):
    pass


class GroupMemberNotEligibleError(Exception):
    pass


class GroupMembershipAlreadyExistsError(Exception):
    pass


class GroupMembershipNotFoundError(Exception):
    pass


class GroupService:
    _organization_managers = {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_group(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        data: GroupCreate,
    ) -> Group:
        organization_role = self._get_organization_role(
            organization_id=organization_id,
            user_id=actor_user_id,
        )
        if organization_role is None:
            raise OrganizationNotFoundError
        if organization_role not in self._organization_managers:
            raise GroupPermissionDeniedError

        group = Group(
            organization_id=organization_id,
            name=data.name,
            description=data.description,
        )
        self.session.add(group)

        try:
            self.session.flush()
        except IntegrityError as exc:
            raise GroupNameAlreadyExistsError from exc

        return group

    def list_groups(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> list[Group]:
        statement = (
            select(Group)
            .join(
                OrganizationMembership,
                OrganizationMembership.organization_id == Group.organization_id,
            )
            .where(
                Group.organization_id == organization_id,
                OrganizationMembership.user_id == actor_user_id,
            )
            .order_by(Group.name)
        )
        groups = list(self.session.scalars(statement))

        if (
            not groups
            and self._get_organization_role(
                organization_id=organization_id,
                user_id=actor_user_id,
            )
            is None
        ):
            raise OrganizationNotFoundError

        return groups

    def add_member(
        self,
        *,
        group_id: UUID,
        actor_user_id: UUID,
        user_id: UUID,
    ) -> GroupMembership:
        group = self._get_manageable_group(
            group_id=group_id,
            actor_user_id=actor_user_id,
        )

        target_membership_id = self.session.scalar(
            select(OrganizationMembership.id).where(
                OrganizationMembership.organization_id == group.organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        if target_membership_id is None:
            raise GroupMemberNotEligibleError

        existing_membership_id = self.session.scalar(
            select(GroupMembership.id)
            .join(Group, Group.id == GroupMembership.group_id)
            .where(
                GroupMembership.group_id == group.id,
                Group.organization_id == group.organization_id,
                GroupMembership.user_id == user_id,
            )
        )
        if existing_membership_id is not None:
            raise GroupMembershipAlreadyExistsError

        membership = GroupMembership(group_id=group.id, user_id=user_id)
        self.session.add(membership)

        try:
            self.session.flush()
        except IntegrityError as exc:
            raise GroupMembershipAlreadyExistsError from exc

        return membership

    def remove_member(
        self,
        *,
        group_id: UUID,
        actor_user_id: UUID,
        user_id: UUID,
    ) -> None:
        group = self._get_manageable_group(
            group_id=group_id,
            actor_user_id=actor_user_id,
        )
        membership = self.session.scalar(
            select(GroupMembership)
            .join(Group, Group.id == GroupMembership.group_id)
            .where(
                GroupMembership.group_id == group.id,
                Group.organization_id == group.organization_id,
                GroupMembership.user_id == user_id,
            )
        )
        if membership is None:
            raise GroupMembershipNotFoundError

        self.session.delete(membership)
        self.session.flush()

    def _get_organization_role(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationRole | None:
        return self.session.scalar(
            select(OrganizationMembership.role).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )

    def _get_manageable_group(
        self,
        *,
        group_id: UUID,
        actor_user_id: UUID,
    ) -> Group:
        statement = (
            select(Group, OrganizationMembership.role)
            .join(
                OrganizationMembership,
                and_(
                    OrganizationMembership.organization_id == Group.organization_id,
                    OrganizationMembership.user_id == actor_user_id,
                ),
            )
            .where(Group.id == group_id)
        )
        access = self.session.execute(statement).one_or_none()
        if access is None:
            raise GroupNotFoundError

        group, organization_role = access
        if organization_role not in self._organization_managers:
            raise GroupPermissionDeniedError

        return group
