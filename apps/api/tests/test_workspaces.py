from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from secure_knowledge_api.dependencies.auth import get_current_user
from secure_knowledge_api.main import app
from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import OrganizationRole, WorkspaceRole
from secure_knowledge_core.database.models import (
    Organization,
    OrganizationMembership,
    User,
    Workspace,
    WorkspaceMembership,
)
from secure_knowledge_core.database.session import get_session
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@dataclass
class ApiContext:
    client: TestClient
    session: Session

    def authenticate_as(self, user: User) -> None:
        app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
def api_context() -> Iterator[ApiContext]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    session = test_session_factory()

    def override_session() -> Iterator[Session]:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as client:
        yield ApiContext(client=client, session=session)

    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_user(session: Session, email: str) -> User:
    user = User(email=email, password_hash="not-used", display_name=email)
    session.add(user)
    session.flush()
    return user


def create_organization(
    session: Session,
    slug: str,
    memberships: list[tuple[User, OrganizationRole]],
) -> Organization:
    organization = Organization(name=slug.title(), slug=slug)
    session.add(organization)
    session.flush()

    for user, role in memberships:
        session.add(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=user.id,
                role=role,
            )
        )
    session.flush()
    return organization


def create_workspace(
    session: Session,
    organization: Organization,
    creator: User,
    slug: str = "knowledge-base",
) -> Workspace:
    workspace = Workspace(
        organization_id=organization.id,
        name=slug.title(),
        slug=slug,
    )
    session.add(workspace)
    session.flush()
    session.add(
        WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=creator.id,
            role=WorkspaceRole.MANAGER,
        )
    )
    session.flush()
    return workspace


def workspace_payload(slug: str = "knowledge-base") -> dict[str, str]:
    return {"name": "Knowledge Base", "slug": slug}


def test_owner_creates_workspace_successfully(api_context: ApiContext) -> None:
    owner = create_user(api_context.session, "owner@example.com")
    organization = create_organization(
        api_context.session,
        "acme",
        [(owner, OrganizationRole.OWNER)],
    )
    api_context.authenticate_as(owner)

    response = api_context.client.post(
        f"/organizations/{organization.id}/workspaces",
        json=workspace_payload(),
    )

    assert response.status_code == 201
    assert response.json()["organization_id"] == str(organization.id)
    assert response.json()["slug"] == "knowledge-base"


def test_member_cannot_create_workspace(api_context: ApiContext) -> None:
    member = create_user(api_context.session, "member@example.com")
    organization = create_organization(
        api_context.session,
        "acme",
        [(member, OrganizationRole.MEMBER)],
    )
    api_context.authenticate_as(member)

    response = api_context.client.post(
        f"/organizations/{organization.id}/workspaces",
        json=workspace_payload(),
    )

    assert response.status_code == 403


def test_workspace_creator_receives_manager_membership(api_context: ApiContext) -> None:
    owner = create_user(api_context.session, "owner@example.com")
    organization = create_organization(
        api_context.session,
        "acme",
        [(owner, OrganizationRole.OWNER)],
    )
    api_context.authenticate_as(owner)

    response = api_context.client.post(
        f"/organizations/{organization.id}/workspaces",
        json=workspace_payload(),
    )

    workspace_id = UUID(response.json()["id"])
    membership = api_context.session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == owner.id,
        )
    )
    assert membership is not None
    assert membership.role is WorkspaceRole.MANAGER


def test_unauthorized_user_cannot_read_workspace(api_context: ApiContext) -> None:
    owner = create_user(api_context.session, "owner@example.com")
    outsider = create_user(api_context.session, "outsider@example.com")
    organization = create_organization(
        api_context.session,
        "acme",
        [(owner, OrganizationRole.OWNER)],
    )
    create_organization(
        api_context.session,
        "other",
        [(outsider, OrganizationRole.OWNER)],
    )
    workspace = create_workspace(api_context.session, organization, owner)
    api_context.authenticate_as(outsider)

    response = api_context.client.get(f"/workspaces/{workspace.id}")

    assert response.status_code == 404


def test_duplicate_workspace_slug_in_one_organization_fails(
    api_context: ApiContext,
) -> None:
    owner = create_user(api_context.session, "owner@example.com")
    organization = create_organization(
        api_context.session,
        "acme",
        [(owner, OrganizationRole.OWNER)],
    )
    api_context.authenticate_as(owner)

    first_response = api_context.client.post(
        f"/organizations/{organization.id}/workspaces",
        json=workspace_payload(),
    )
    duplicate_response = api_context.client.post(
        f"/organizations/{organization.id}/workspaces",
        json=workspace_payload(),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409


def test_same_workspace_slug_in_another_organization_succeeds(
    api_context: ApiContext,
) -> None:
    owner = create_user(api_context.session, "owner@example.com")
    first_organization = create_organization(
        api_context.session,
        "acme",
        [(owner, OrganizationRole.OWNER)],
    )
    second_organization = create_organization(
        api_context.session,
        "other",
        [(owner, OrganizationRole.OWNER)],
    )
    api_context.authenticate_as(owner)

    first_response = api_context.client.post(
        f"/organizations/{first_organization.id}/workspaces",
        json=workspace_payload(),
    )
    second_response = api_context.client.post(
        f"/organizations/{second_organization.id}/workspaces",
        json=workspace_payload(),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201


def test_manager_can_add_member(api_context: ApiContext) -> None:
    manager = create_user(api_context.session, "manager@example.com")
    member = create_user(api_context.session, "member@example.com")
    organization = create_organization(
        api_context.session,
        "acme",
        [
            (manager, OrganizationRole.MEMBER),
            (member, OrganizationRole.MEMBER),
        ],
    )
    workspace = create_workspace(api_context.session, organization, manager)
    api_context.authenticate_as(manager)

    response = api_context.client.post(
        f"/workspaces/{workspace.id}/members",
        json={"user_id": str(member.id), "role": "member"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == str(member.id)
    assert response.json()["role"] == "member"


def test_viewer_cannot_manage_membership(api_context: ApiContext) -> None:
    owner = create_user(api_context.session, "owner@example.com")
    viewer = create_user(api_context.session, "viewer@example.com")
    member = create_user(api_context.session, "member@example.com")
    organization = create_organization(
        api_context.session,
        "acme",
        [
            (owner, OrganizationRole.OWNER),
            (viewer, OrganizationRole.MEMBER),
            (member, OrganizationRole.MEMBER),
        ],
    )
    workspace = create_workspace(api_context.session, organization, owner)
    api_context.session.add(
        WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=viewer.id,
            role=WorkspaceRole.VIEWER,
        )
    )
    api_context.session.flush()
    api_context.authenticate_as(viewer)

    response = api_context.client.post(
        f"/workspaces/{workspace.id}/members",
        json={"user_id": str(member.id), "role": "member"},
    )

    assert response.status_code == 403


def test_cross_tenant_membership_assignment_is_rejected(
    api_context: ApiContext,
) -> None:
    manager = create_user(api_context.session, "manager@example.com")
    outsider = create_user(api_context.session, "outsider@example.com")
    organization = create_organization(
        api_context.session,
        "acme",
        [(manager, OrganizationRole.MEMBER)],
    )
    create_organization(
        api_context.session,
        "other",
        [(outsider, OrganizationRole.MEMBER)],
    )
    workspace = create_workspace(api_context.session, organization, manager)
    api_context.authenticate_as(manager)

    response = api_context.client.post(
        f"/workspaces/{workspace.id}/members",
        json={"user_id": str(outsider.id), "role": "member"},
    )

    assert response.status_code == 403


def test_organization_member_can_list_workspaces(api_context: ApiContext) -> None:
    owner = create_user(api_context.session, "owner@example.com")
    member = create_user(api_context.session, "member@example.com")
    organization = create_organization(
        api_context.session,
        "acme",
        [
            (owner, OrganizationRole.OWNER),
            (member, OrganizationRole.MEMBER),
        ],
    )
    workspace = create_workspace(api_context.session, organization, owner)
    api_context.authenticate_as(member)

    response = api_context.client.get(
        f"/organizations/{organization.id}/workspaces",
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(workspace.id)]
