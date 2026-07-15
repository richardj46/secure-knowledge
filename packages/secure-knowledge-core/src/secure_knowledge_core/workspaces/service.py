from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from secure_knowledge_core.database.enums import OrganizationRole, WorkspaceRole
from secure_knowledge_core.database.models import (
    OrganizationMembership,
    Workspace,
    WorkspaceMembership,
)
from secure_knowledge_core.workspaces.schemas import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
)


class OrganizationNotFoundError(Exception):
    pass


class WorkspaceNotFoundError(Exception):
    pass


class WorkspacePermissionDeniedError(Exception):
    pass


class WorkspaceSlugAlreadyExistsError(Exception):
    pass


class WorkspaceMemberNotEligibleError(Exception):
    pass


class WorkspaceMembershipAlreadyExistsError(Exception):
    pass


class WorkspaceService:
    _organization_managers = {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_workspace(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        data: WorkspaceCreate,
    ) -> Workspace:
        organization_role = self._get_organization_role(
            organization_id=organization_id,
            user_id=actor_user_id,
        )
        if organization_role is None:
            raise OrganizationNotFoundError
        if organization_role not in self._organization_managers:
            raise WorkspacePermissionDeniedError

        workspace = Workspace(
            organization_id=organization_id,
            name=data.name,
            slug=data.slug,
        )
        self.session.add(workspace)

        try:
            self.session.flush()
        except IntegrityError as exc:
            raise WorkspaceSlugAlreadyExistsError from exc

        self.session.add(
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=actor_user_id,
                role=WorkspaceRole.MANAGER,
            )
        )
        self.session.flush()

        return workspace

    def list_workspaces(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> list[Workspace]:
        statement = (
            select(Workspace)
            .join(
                OrganizationMembership,
                OrganizationMembership.organization_id == Workspace.organization_id,
            )
            .where(
                Workspace.organization_id == organization_id,
                OrganizationMembership.user_id == actor_user_id,
            )
            .order_by(Workspace.created_at)
        )
        workspaces = list(self.session.scalars(statement))

        if (
            not workspaces
            and self._get_organization_role(
                organization_id=organization_id,
                user_id=actor_user_id,
            )
            is None
        ):
            raise OrganizationNotFoundError

        return workspaces

    def get_workspace(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> Workspace:
        statement = (
            select(Workspace)
            .join(
                OrganizationMembership,
                OrganizationMembership.organization_id == Workspace.organization_id,
            )
            .where(
                Workspace.id == workspace_id,
                OrganizationMembership.user_id == actor_user_id,
            )
        )
        workspace = self.session.scalar(statement)
        if workspace is None:
            raise WorkspaceNotFoundError

        return workspace

    def add_member(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        data: WorkspaceMemberCreate,
    ) -> WorkspaceMembership:
        workspace, organization_role, workspace_role = self._get_workspace_access(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
        )
        if organization_role not in self._organization_managers and (
            workspace_role is not WorkspaceRole.MANAGER
        ):
            raise WorkspacePermissionDeniedError

        target_membership_id = self.session.scalar(
            select(OrganizationMembership.id).where(
                OrganizationMembership.organization_id == workspace.organization_id,
                OrganizationMembership.user_id == data.user_id,
            )
        )
        if target_membership_id is None:
            raise WorkspaceMemberNotEligibleError

        existing_membership_id = self.session.scalar(
            select(WorkspaceMembership.id)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .where(
                WorkspaceMembership.workspace_id == workspace.id,
                Workspace.organization_id == workspace.organization_id,
                WorkspaceMembership.user_id == data.user_id,
            )
        )
        if existing_membership_id is not None:
            raise WorkspaceMembershipAlreadyExistsError

        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=data.user_id,
            role=data.role,
        )
        self.session.add(membership)

        try:
            self.session.flush()
        except IntegrityError as exc:
            raise WorkspaceMembershipAlreadyExistsError from exc

        return membership

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

    def _get_workspace_access(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> tuple[Workspace, OrganizationRole, WorkspaceRole | None]:
        actor_organization_membership = aliased(OrganizationMembership)
        actor_workspace_membership = aliased(WorkspaceMembership)

        statement = (
            select(
                Workspace,
                actor_organization_membership.role,
                actor_workspace_membership.role,
            )
            .join(
                actor_organization_membership,
                and_(
                    actor_organization_membership.organization_id == Workspace.organization_id,
                    actor_organization_membership.user_id == actor_user_id,
                ),
            )
            .outerjoin(
                actor_workspace_membership,
                and_(
                    actor_workspace_membership.workspace_id == Workspace.id,
                    actor_workspace_membership.user_id == actor_user_id,
                ),
            )
            .where(Workspace.id == workspace_id)
        )
        access = self.session.execute(statement).one_or_none()
        if access is None:
            raise WorkspaceNotFoundError

        workspace, organization_role, workspace_role = access
        return workspace, organization_role, workspace_role
