from uuid import UUID

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from secure_knowledge_core.database.enums import (
    DocumentPermissionLevel,
    DocumentStatus,
    DocumentVisibility,
    OrganizationRole,
    WorkspaceRole,
)
from secure_knowledge_core.database.models import (
    Document,
    DocumentGroupPermission,
    DocumentUserPermission,
    Group,
    GroupMembership,
    OrganizationMembership,
    Workspace,
    WorkspaceMembership,
)
from secure_knowledge_core.documents.schemas import (
    DocumentCreate,
    DocumentGroupPermissionAdd,
    DocumentUserPermissionAdd,
)


class WorkspaceNotFoundError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


class DocumentPermissionDeniedError(Exception):
    pass


class DocumentSlugAlreadyExistsError(Exception):
    pass


class DocumentPermissionTargetNotEligibleError(Exception):
    pass


class DocumentPermissionAlreadyExistsError(Exception):
    pass


class DocumentPermissionNotFoundError(Exception):
    pass


class DocumentService:
    _organization_managers = {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_document(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        data: DocumentCreate,
    ) -> Document:
        workspace, organization_role, workspace_role = self._get_workspace_access(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
        )
        if organization_role not in self._organization_managers and (
            workspace_role is not WorkspaceRole.MANAGER
        ):
            raise DocumentPermissionDeniedError

        document = Document(
            organization_id=workspace.organization_id,
            workspace_id=workspace.id,
            owner_user_id=actor_user_id,
            title=data.title,
            slug=data.slug,
            source_filename=data.source_filename,
            mime_type=data.mime_type,
            storage_key=None,
            visibility=data.visibility,
            status=DocumentStatus.PENDING,
            current_version_number=1,
        )
        self.session.add(document)

        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DocumentSlugAlreadyExistsError from exc

        return document

    def list_documents(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> list[Document]:
        self._require_workspace_organization_membership(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
        )
        statement = (
            select(Document)
            .where(
                Document.workspace_id == workspace_id,
                self.authorized_document_condition(actor_user_id),
            )
            .order_by(Document.created_at)
        )
        return list(self.session.scalars(statement))

    def get_document(
        self,
        *,
        document_id: UUID,
        actor_user_id: UUID,
    ) -> Document:
        document = self.session.scalar(
            select(Document).where(
                Document.id == document_id,
                self.authorized_document_condition(actor_user_id),
            )
        )
        if document is None:
            raise DocumentNotFoundError

        return document

    def add_user_permission(
        self,
        *,
        document_id: UUID,
        actor_user_id: UUID,
        data: DocumentUserPermissionAdd,
    ) -> DocumentUserPermission:
        document = self._get_manageable_document(
            document_id=document_id,
            actor_user_id=actor_user_id,
        )
        target_membership_id = self.session.scalar(
            select(OrganizationMembership.id).where(
                OrganizationMembership.organization_id == document.organization_id,
                OrganizationMembership.user_id == data.user_id,
            )
        )
        if target_membership_id is None:
            raise DocumentPermissionTargetNotEligibleError

        permission = DocumentUserPermission(
            document_id=document.id,
            user_id=data.user_id,
            level=data.level,
        )
        self.session.add(permission)

        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DocumentPermissionAlreadyExistsError from exc

        return permission

    def add_group_permission(
        self,
        *,
        document_id: UUID,
        actor_user_id: UUID,
        data: DocumentGroupPermissionAdd,
    ) -> DocumentGroupPermission:
        document = self._get_manageable_document(
            document_id=document_id,
            actor_user_id=actor_user_id,
        )
        group_id = self.session.scalar(
            select(Group.id).where(
                Group.id == data.group_id,
                Group.organization_id == document.organization_id,
            )
        )
        if group_id is None:
            raise DocumentPermissionTargetNotEligibleError

        permission = DocumentGroupPermission(
            document_id=document.id,
            group_id=data.group_id,
            level=data.level,
        )
        self.session.add(permission)

        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DocumentPermissionAlreadyExistsError from exc

        return permission

    def remove_user_permission(
        self,
        *,
        document_id: UUID,
        actor_user_id: UUID,
        user_id: UUID,
    ) -> None:
        document = self._get_manageable_document(
            document_id=document_id,
            actor_user_id=actor_user_id,
        )
        permission = self.session.scalar(
            select(DocumentUserPermission).where(
                DocumentUserPermission.document_id == document.id,
                DocumentUserPermission.user_id == user_id,
            )
        )
        if permission is None:
            raise DocumentPermissionNotFoundError

        self.session.delete(permission)
        self.session.flush()

    def remove_group_permission(
        self,
        *,
        document_id: UUID,
        actor_user_id: UUID,
        group_id: UUID,
    ) -> None:
        document = self._get_manageable_document(
            document_id=document_id,
            actor_user_id=actor_user_id,
        )
        permission = self.session.scalar(
            select(DocumentGroupPermission)
            .join(Group, Group.id == DocumentGroupPermission.group_id)
            .where(
                DocumentGroupPermission.document_id == document.id,
                DocumentGroupPermission.group_id == group_id,
                Group.organization_id == document.organization_id,
            )
        )
        if permission is None:
            raise DocumentPermissionNotFoundError

        self.session.delete(permission)
        self.session.flush()

    @staticmethod
    def authorized_document_condition(actor_user_id: UUID):
        organization_member = exists().where(
            OrganizationMembership.organization_id == Document.organization_id,
            OrganizationMembership.user_id == actor_user_id,
        )
        organization_manager = exists().where(
            OrganizationMembership.organization_id == Document.organization_id,
            OrganizationMembership.user_id == actor_user_id,
            OrganizationMembership.role.in_(
                [OrganizationRole.OWNER, OrganizationRole.ADMIN]
            ),
        )
        workspace_member = exists().where(
            WorkspaceMembership.workspace_id == Document.workspace_id,
            WorkspaceMembership.user_id == actor_user_id,
        )
        direct_permission = exists().where(
            DocumentUserPermission.document_id == Document.id,
            DocumentUserPermission.user_id == actor_user_id,
        )
        group_permission = (
            exists()
            .select_from(DocumentGroupPermission)
            .join(Group, Group.id == DocumentGroupPermission.group_id)
            .join(GroupMembership, GroupMembership.group_id == Group.id)
            .where(
                DocumentGroupPermission.document_id == Document.id,
                Group.organization_id == Document.organization_id,
                GroupMembership.user_id == actor_user_id,
            )
        )

        return and_(
            organization_member,
            or_(
                organization_manager,
                Document.owner_user_id == actor_user_id,
                direct_permission,
                group_permission,
                Document.visibility == DocumentVisibility.ORGANIZATION,
                and_(
                    Document.visibility == DocumentVisibility.WORKSPACE,
                    workspace_member,
                ),
            ),
        )

    def _get_manageable_document(
        self,
        *,
        document_id: UUID,
        actor_user_id: UUID,
    ) -> Document:
        actor_organization_membership = aliased(OrganizationMembership)
        document = self.session.scalar(
            select(Document)
            .join(
                actor_organization_membership,
                and_(
                    actor_organization_membership.organization_id
                    == Document.organization_id,
                    actor_organization_membership.user_id == actor_user_id,
                ),
            )
            .where(Document.id == document_id)
        )
        if document is None:
            raise DocumentNotFoundError

        if document.owner_user_id == actor_user_id:
            return document

        can_manage = self.session.scalar(
            select(
                or_(
                    exists().where(
                        OrganizationMembership.organization_id
                        == document.organization_id,
                        OrganizationMembership.user_id == actor_user_id,
                        OrganizationMembership.role.in_(
                            [OrganizationRole.OWNER, OrganizationRole.ADMIN]
                        ),
                    ),
                    exists().where(
                        WorkspaceMembership.workspace_id == document.workspace_id,
                        WorkspaceMembership.user_id == actor_user_id,
                        WorkspaceMembership.role == WorkspaceRole.MANAGER,
                    ),
                    exists().where(
                        DocumentUserPermission.document_id == document.id,
                        DocumentUserPermission.user_id == actor_user_id,
                        DocumentUserPermission.level
                        == DocumentPermissionLevel.MANAGER,
                    ),
                    exists()
                    .select_from(DocumentGroupPermission)
                    .join(
                        GroupMembership,
                        GroupMembership.group_id
                        == DocumentGroupPermission.group_id,
                    )
                    .join(Group, Group.id == DocumentGroupPermission.group_id)
                    .where(
                        DocumentGroupPermission.document_id == document.id,
                        DocumentGroupPermission.level
                        == DocumentPermissionLevel.MANAGER,
                        Group.organization_id == document.organization_id,
                        GroupMembership.user_id == actor_user_id,
                    ),
                )
            )
        )
        if not can_manage:
            raise DocumentPermissionDeniedError

        return document

    def _get_workspace_access(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> tuple[Workspace, OrganizationRole, WorkspaceRole | None]:
        actor_organization_membership = aliased(OrganizationMembership)
        actor_workspace_membership = aliased(WorkspaceMembership)

        access = self.session.execute(
            select(
                Workspace,
                actor_organization_membership.role,
                actor_workspace_membership.role,
            )
            .join(
                actor_organization_membership,
                and_(
                    actor_organization_membership.organization_id
                    == Workspace.organization_id,
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
        ).one_or_none()
        if access is None:
            raise WorkspaceNotFoundError

        workspace, organization_role, workspace_role = access
        return workspace, organization_role, workspace_role

    def _require_workspace_organization_membership(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        workspace = self.session.scalar(
            select(Workspace.id)
            .join(
                OrganizationMembership,
                OrganizationMembership.organization_id == Workspace.organization_id,
            )
            .where(
                Workspace.id == workspace_id,
                OrganizationMembership.user_id == actor_user_id,
            )
        )
        if workspace is None:
            raise WorkspaceNotFoundError
