from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from secure_knowledge_api.dependencies.auth import get_current_user
from secure_knowledge_api.dependencies.llm import get_answer_provider
from secure_knowledge_api.dependencies.retrieval import get_retrieval_service
from secure_knowledge_api.main import app
from secure_knowledge_core.answers.schemas import CitationDraft, GeneratedAnswer
from secure_knowledge_core.database.base import Base
from secure_knowledge_core.database.enums import (
    Answerability,
    DocumentPermissionLevel,
    DocumentStatus,
    DocumentVersionStatus,
    DocumentVisibility,
    OrganizationRole,
    WorkspaceRole,
)
from secure_knowledge_core.database.models import (
    AnswerCitation,
    AnswerRun,
    Document,
    DocumentChunk,
    DocumentGroupPermission,
    DocumentUserPermission,
    DocumentVersion,
    Group,
    GroupMembership,
    Organization,
    OrganizationMembership,
    RetrievalResultRecord,
    RetrievalRun,
    User,
    Workspace,
    WorkspaceMembership,
)
from secure_knowledge_core.database.session import get_session
from secure_knowledge_core.llm.fake import FakeAnswerProvider
from secure_knowledge_core.retrieval import service as retrieval_service_module
from secure_knowledge_core.retrieval.fusion import (
    FusedChunk,
    reciprocal_rank_fusion,
)
from secure_knowledge_core.retrieval.repository import (
    RankedChunk,
    build_retrievable_chunk_condition,
)
from secure_knowledge_core.retrieval.service import RetrievalService


@dataclass
class RetrievalSecurityScenario:
    client: TestClient
    session: Session
    organization_a: Organization
    organization_b: Organization
    engineering: Workspace
    finance: Workspace
    confidential: Workspace
    alice: User
    bob: User
    carol: User
    charlie: User
    public_guide: Document
    incident_report: Document
    payroll_policy: Document
    acquisition_plan: Document

    def authenticate_as(self, user: User) -> None:
        app.dependency_overrides[get_current_user] = lambda: user


def create_user(session: Session, name: str) -> User:
    user = User(
        email=f"{name.lower()}@example.com",
        password_hash="not-used",
        display_name=name,
    )
    session.add(user)
    session.flush()
    return user


def create_organization(
    session: Session,
    *,
    slug: str,
    memberships: list[tuple[User, OrganizationRole]],
) -> Organization:
    organization = Organization(name=slug.title(), slug=slug)
    session.add(organization)
    session.flush()

    session.add_all(
        [
            OrganizationMembership(
                organization_id=organization.id,
                user_id=user.id,
                role=role,
            )
            for user, role in memberships
        ]
    )
    session.flush()
    return organization


def create_workspace(
    session: Session,
    *,
    organization: Organization,
    slug: str,
    memberships: list[tuple[User, WorkspaceRole]],
) -> Workspace:
    workspace = Workspace(
        organization_id=organization.id,
        name=slug.title(),
        slug=slug,
    )
    session.add(workspace)
    session.flush()

    session.add_all(
        [
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user.id,
                role=role,
            )
            for user, role in memberships
        ]
    )
    session.flush()
    return workspace


def create_document(
    session: Session,
    *,
    workspace: Workspace,
    owner: User,
    slug: str,
    visibility: DocumentVisibility,
    status: DocumentStatus = DocumentStatus.READY,
    version_status: DocumentVersionStatus = DocumentVersionStatus.READY,
    content: str,
) -> tuple[Document, DocumentVersion, DocumentChunk]:
    document = Document(
        organization_id=workspace.organization_id,
        workspace_id=workspace.id,
        owner_user_id=owner.id,
        title=slug.replace("-", " ").title(),
        slug=slug,
        source_filename=f"{slug}.txt",
        mime_type="text/plain",
        visibility=visibility,
        status=status,
        current_version_number=1,
    )
    session.add(document)
    session.flush()

    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        storage_key=f"test/{uuid4()}",
        checksum="test-checksum",
        file_size_bytes=len(content),
        status=version_status,
    )
    session.add(version)
    session.flush()

    chunk = DocumentChunk(
        organization_id=workspace.organization_id,
        workspace_id=workspace.id,
        document_id=document.id,
        document_version_id=version.id,
        chunk_index=0,
        content=content,
        token_count=len(content.split()),
        chunk_metadata={},
        embedding=[1.0, 0.0],
    )
    session.add(chunk)
    session.flush()
    return document, version, chunk


def add_document_version(
    session: Session,
    *,
    document: Document,
    workspace: Workspace,
    version_number: int,
    content: str,
) -> DocumentChunk:
    version = DocumentVersion(
        document_id=document.id,
        version_number=version_number,
        storage_key=f"test/{uuid4()}",
        checksum=f"checksum-{version_number}",
        file_size_bytes=len(content),
        status=DocumentVersionStatus.READY,
    )
    session.add(version)
    session.flush()

    chunk = DocumentChunk(
        organization_id=workspace.organization_id,
        workspace_id=workspace.id,
        document_id=document.id,
        document_version_id=version.id,
        chunk_index=0,
        content=content,
        token_count=len(content.split()),
        chunk_metadata={},
        embedding=[1.0, 0.0],
    )
    session.add(chunk)
    session.flush()
    return chunk


@pytest.fixture
def security_scenario() -> Iterator[RetrievalSecurityScenario]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_factory()

    alice = create_user(session, "Alice")
    bob = create_user(session, "Bob")
    carol = create_user(session, "Carol")
    charlie = create_user(session, "Charlie")

    organization_a = create_organization(
        session,
        slug="organization-a",
        memberships=[
            (alice, OrganizationRole.OWNER),
            (bob, OrganizationRole.MEMBER),
            (carol, OrganizationRole.MEMBER),
        ],
    )
    organization_b = create_organization(
        session,
        slug="organization-b",
        memberships=[(charlie, OrganizationRole.OWNER)],
    )

    engineering = create_workspace(
        session,
        organization=organization_a,
        slug="engineering",
        memberships=[
            (alice, WorkspaceRole.MANAGER),
            (bob, WorkspaceRole.MEMBER),
        ],
    )
    finance = create_workspace(
        session,
        organization=organization_a,
        slug="finance",
        memberships=[(alice, WorkspaceRole.MANAGER)],
    )
    confidential = create_workspace(
        session,
        organization=organization_b,
        slug="confidential",
        memberships=[(charlie, WorkspaceRole.MANAGER)],
    )

    public_guide, _, _ = create_document(
        session,
        workspace=engineering,
        owner=alice,
        slug="public-engineering-guide",
        visibility=DocumentVisibility.ORGANIZATION,
        content="outdated engineering guide",
    )
    public_guide.current_version_number = 2
    add_document_version(
        session,
        document=public_guide,
        workspace=engineering,
        version_number=2,
        content="current public engineering guide",
    )
    incident_report, _, _ = create_document(
        session,
        workspace=engineering,
        owner=alice,
        slug="restricted-incident-report",
        visibility=DocumentVisibility.RESTRICTED,
        content="restricted incident report",
    )
    payroll_policy, _, _ = create_document(
        session,
        workspace=finance,
        owner=alice,
        slug="payroll-policy",
        visibility=DocumentVisibility.WORKSPACE,
        content="finance payroll policy",
    )
    acquisition_plan, _, _ = create_document(
        session,
        workspace=confidential,
        owner=charlie,
        slug="acquisition-plan",
        visibility=DocumentVisibility.OWNER,
        content="confidential acquisition plan",
    )
    create_document(
        session,
        workspace=engineering,
        owner=alice,
        slug="failed-document",
        visibility=DocumentVisibility.ORGANIZATION,
        status=DocumentStatus.FAILED,
        version_status=DocumentVersionStatus.FAILED,
        content="failed document content",
    )
    create_document(
        session,
        workspace=engineering,
        owner=alice,
        slug="processing-document",
        visibility=DocumentVisibility.ORGANIZATION,
        status=DocumentStatus.EMBEDDING,
        version_status=DocumentVersionStatus.EMBEDDING,
        content="processing document content",
    )
    session.flush()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_retrieval_service] = lambda: RetrievalService(
        session=session,
        embedding_provider=DeterministicEmbeddingProvider(),
    )

    with TestClient(app) as client:
        yield RetrievalSecurityScenario(
            client=client,
            session=session,
            organization_a=organization_a,
            organization_b=organization_b,
            engineering=engineering,
            finance=finance,
            confidential=confidential,
            alice=alice,
            bob=bob,
            carol=carol,
            charlie=charlie,
            public_guide=public_guide,
            incident_report=incident_report,
            payroll_policy=payroll_policy,
            acquisition_plan=acquisition_plan,
        )

    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def retrieve_contents(
    scenario: RetrievalSecurityScenario,
    *,
    user: User,
    organization: Organization,
) -> set[str]:
    statement = (
        select(DocumentChunk.content)
        .join(Document, Document.id == DocumentChunk.document_id)
        .join(
            DocumentVersion,
            DocumentVersion.id == DocumentChunk.document_version_id,
        )
        .where(
            build_retrievable_chunk_condition(
                user_id=user.id,
                organization_id=organization.id,
            )
        )
    )
    return set(scenario.session.scalars(statement))


def test_owner_retrieval_is_tenant_scoped(
    security_scenario: RetrievalSecurityScenario,
) -> None:
    organization_a_results = retrieve_contents(
        security_scenario,
        user=security_scenario.alice,
        organization=security_scenario.organization_a,
    )
    organization_b_results = retrieve_contents(
        security_scenario,
        user=security_scenario.alice,
        organization=security_scenario.organization_b,
    )

    assert organization_a_results == {
        "current public engineering guide",
        "restricted incident report",
        "finance payroll policy",
    }
    assert organization_b_results == set()


def test_workspace_member_cannot_retrieve_other_workspace_content(
    security_scenario: RetrievalSecurityScenario,
) -> None:
    results = retrieve_contents(
        security_scenario,
        user=security_scenario.bob,
        organization=security_scenario.organization_a,
    )

    assert "current public engineering guide" in results
    assert "finance payroll policy" not in results
    assert "restricted incident report" not in results


def test_organization_member_only_retrieves_organization_visible_documents(
    security_scenario: RetrievalSecurityScenario,
) -> None:
    results = retrieve_contents(
        security_scenario,
        user=security_scenario.carol,
        organization=security_scenario.organization_a,
    )

    assert results == {"current public engineering guide"}


def test_cross_tenant_user_never_retrieves_chunks(
    security_scenario: RetrievalSecurityScenario,
) -> None:
    results = retrieve_contents(
        security_scenario,
        user=security_scenario.charlie,
        organization=security_scenario.organization_a,
    )

    assert results == set()


def test_direct_permission_addition_and_removal_take_effect_immediately(
    security_scenario: RetrievalSecurityScenario,
) -> None:
    permission = DocumentUserPermission(
        document_id=security_scenario.incident_report.id,
        user_id=security_scenario.bob.id,
        level=DocumentPermissionLevel.VIEWER,
    )
    security_scenario.session.add(permission)
    security_scenario.session.flush()

    granted_results = retrieve_contents(
        security_scenario,
        user=security_scenario.bob,
        organization=security_scenario.organization_a,
    )
    assert "restricted incident report" in granted_results

    security_scenario.session.delete(permission)
    security_scenario.session.flush()

    revoked_results = retrieve_contents(
        security_scenario,
        user=security_scenario.bob,
        organization=security_scenario.organization_a,
    )
    assert "restricted incident report" not in revoked_results


def test_group_membership_addition_and_removal_take_effect_immediately(
    security_scenario: RetrievalSecurityScenario,
) -> None:
    group = Group(
        organization_id=security_scenario.organization_a.id,
        name="Incident Responders",
    )
    security_scenario.session.add(group)
    security_scenario.session.flush()
    security_scenario.session.add(
        DocumentGroupPermission(
            document_id=security_scenario.incident_report.id,
            group_id=group.id,
            level=DocumentPermissionLevel.VIEWER,
        )
    )
    membership = GroupMembership(
        group_id=group.id,
        user_id=security_scenario.carol.id,
    )
    security_scenario.session.add(membership)
    security_scenario.session.flush()

    granted_results = retrieve_contents(
        security_scenario,
        user=security_scenario.carol,
        organization=security_scenario.organization_a,
    )
    assert "restricted incident report" in granted_results

    security_scenario.session.delete(membership)
    security_scenario.session.flush()

    revoked_results = retrieve_contents(
        security_scenario,
        user=security_scenario.carol,
        organization=security_scenario.organization_a,
    )
    assert "restricted incident report" not in revoked_results


def test_old_failed_and_processing_chunks_never_appear(
    security_scenario: RetrievalSecurityScenario,
) -> None:
    results = retrieve_contents(
        security_scenario,
        user=security_scenario.alice,
        organization=security_scenario.organization_a,
    )

    assert "current public engineering guide" in results
    assert "outdated engineering guide" not in results
    assert "failed document content" not in results
    assert "processing document content" not in results


def test_workspace_filters_do_not_disclose_cross_tenant_workspace_existence(
    security_scenario: RetrievalSecurityScenario,
) -> None:
    security_scenario.authenticate_as(security_scenario.bob)
    path = (
        f"/organizations/{security_scenario.organization_a.id}/retrieval/search"
    )

    cross_tenant_response = security_scenario.client.post(
        path,
        json={
            "query": "acquisition",
            "workspace_ids": [str(security_scenario.confidential.id)],
            "limit": 10,
        },
    )
    missing_response = security_scenario.client.post(
        path,
        json={
            "query": "acquisition",
            "workspace_ids": [str(uuid4())],
            "limit": 10,
        },
    )

    assert cross_tenant_response.status_code == 404
    assert missing_response.status_code == 404
    assert cross_tenant_response.json() == missing_response.json()


class DeterministicEmbeddingProvider:
    model = "deterministic-security-test"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


@dataclass
class RetrievalStageCapture:
    vector_chunk_ids: list[UUID]
    keyword_chunk_ids: list[UUID]
    fusion_vector_chunk_ids: list[UUID]
    fusion_keyword_chunk_ids: list[UUID]


class RecordingAuthorizedRepository:
    def __init__(
        self,
        session: Session,
        capture: RetrievalStageCapture,
    ) -> None:
        self.session = session
        self.capture = capture

    def _authorized_chunks(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        workspace_ids: list[UUID],
    ) -> list[RankedChunk]:
        statement = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                Document.title,
                DocumentChunk.content,
                DocumentChunk.page_number,
                DocumentChunk.section_title,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .join(
                DocumentVersion,
                DocumentVersion.id == DocumentChunk.document_version_id,
            )
            .where(
                build_retrievable_chunk_condition(
                    user_id=user_id,
                    organization_id=organization_id,
                )
            )
        )
        if workspace_ids:
            statement = statement.where(Document.workspace_id.in_(workspace_ids))

        rows = self.session.execute(statement).all()
        return [
            RankedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                document_title=row.title,
                content=row.content,
                page_number=row.page_number,
                section_title=row.section_title,
                score=0.0,
                rank=index,
            )
            for index, row in enumerate(rows, start=1)
        ]

    def vector_search(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        query_embedding: list[float],
        workspace_ids: list[UUID],
        limit: int,
    ) -> list[RankedChunk]:
        del query_embedding
        candidates = self._authorized_chunks(
            user_id=user_id,
            organization_id=organization_id,
            workspace_ids=workspace_ids,
        )[:limit]
        self.capture.vector_chunk_ids = [item.chunk_id for item in candidates]
        return candidates

    def keyword_search(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        query: str,
        workspace_ids: list[UUID],
        limit: int,
    ) -> list[RankedChunk]:
        del query
        candidates = self._authorized_chunks(
            user_id=user_id,
            organization_id=organization_id,
            workspace_ids=workspace_ids,
        )[:limit]
        self.capture.keyword_chunk_ids = [item.chunk_id for item in candidates]
        return candidates


def install_recording_retrieval(
    monkeypatch: pytest.MonkeyPatch,
    *,
    scenario: RetrievalSecurityScenario,
) -> RetrievalStageCapture:
    capture = RetrievalStageCapture([], [], [], [])
    repository = RecordingAuthorizedRepository(scenario.session, capture)
    app.dependency_overrides[get_retrieval_service] = lambda: RetrievalService(
        session=scenario.session,
        embedding_provider=DeterministicEmbeddingProvider(),
        repository=repository,
    )

    def capture_fusion(
        *,
        vector_results: list[RankedChunk],
        keyword_results: list[RankedChunk],
        k: int = 60,
    ) -> list[FusedChunk]:
        capture.fusion_vector_chunk_ids = [item.chunk_id for item in vector_results]
        capture.fusion_keyword_chunk_ids = [item.chunk_id for item in keyword_results]
        return reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            k=k,
        )

    monkeypatch.setattr(
        retrieval_service_module,
        "reciprocal_rank_fusion",
        capture_fusion,
    )
    return capture


def assert_chunk_absent_from_trace(
    scenario: RetrievalSecurityScenario,
    *,
    forbidden_chunk_id: UUID,
) -> None:
    run = scenario.session.scalar(select(RetrievalRun))
    assert run is not None
    traced_chunk_ids = set(
        scenario.session.scalars(
            select(RetrievalResultRecord.chunk_id).where(
                RetrievalResultRecord.retrieval_run_id == run.id
            )
        )
    )
    assert forbidden_chunk_id not in traced_chunk_ids


def test_exact_cross_tenant_match_never_enters_retrieval_pipeline(
    security_scenario: RetrievalSecurityScenario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbidden_chunk = security_scenario.session.scalar(
        select(DocumentChunk).where(
            DocumentChunk.document_id == security_scenario.acquisition_plan.id
        )
    )
    assert forbidden_chunk is not None
    forbidden_chunk.content = "The confidential acquisition code name is Blue Heron."
    security_scenario.session.flush()

    capture = install_recording_retrieval(
        monkeypatch,
        scenario=security_scenario,
    )
    security_scenario.authenticate_as(security_scenario.bob)
    response = security_scenario.client.post(
        f"/organizations/{security_scenario.organization_a.id}/retrieval/search",
        json={"query": "What is the acquisition code name?", "limit": 10},
    )

    assert response.status_code == 200
    assert forbidden_chunk.id not in capture.vector_chunk_ids
    assert forbidden_chunk.id not in capture.keyword_chunk_ids
    assert forbidden_chunk.id not in capture.fusion_vector_chunk_ids
    assert forbidden_chunk.id not in capture.fusion_keyword_chunk_ids
    assert all(
        result["chunk_id"] != str(forbidden_chunk.id)
        for result in response.json()["results"]
    )
    assert_chunk_absent_from_trace(
        security_scenario,
        forbidden_chunk_id=forbidden_chunk.id,
    )


def test_exact_inaccessible_workspace_match_never_enters_retrieval_pipeline(
    security_scenario: RetrievalSecurityScenario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbidden_chunk = security_scenario.session.scalar(
        select(DocumentChunk).where(
            DocumentChunk.document_id == security_scenario.payroll_policy.id
        )
    )
    assert forbidden_chunk is not None
    forbidden_chunk.content = "The exact employee payroll routing phrase is ORCHID-774."
    create_document(
        security_scenario.session,
        workspace=security_scenario.engineering,
        owner=security_scenario.alice,
        slug="general-employee-handbook",
        visibility=DocumentVisibility.ORGANIZATION,
        content="General employee handbook and workplace guidance.",
    )
    security_scenario.session.flush()

    capture = install_recording_retrieval(
        monkeypatch,
        scenario=security_scenario,
    )
    security_scenario.authenticate_as(security_scenario.bob)
    response = security_scenario.client.post(
        f"/organizations/{security_scenario.organization_a.id}/retrieval/search",
        json={"query": "exact employee payroll routing phrase ORCHID-774", "limit": 10},
    )

    assert response.status_code == 200
    assert forbidden_chunk.id not in capture.vector_chunk_ids
    assert forbidden_chunk.id not in capture.keyword_chunk_ids
    assert forbidden_chunk.id not in capture.fusion_vector_chunk_ids
    assert forbidden_chunk.id not in capture.fusion_keyword_chunk_ids
    assert all(
        result["chunk_id"] != str(forbidden_chunk.id)
        for result in response.json()["results"]
    )
    assert_chunk_absent_from_trace(
        security_scenario,
        forbidden_chunk_id=forbidden_chunk.id,
    )


def test_answer_endpoint_uses_injected_fake_provider_with_authorized_citation(
    security_scenario: RetrievalSecurityScenario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorized_chunk = security_scenario.session.scalar(
        select(DocumentChunk)
        .join(
            DocumentVersion,
            DocumentVersion.id == DocumentChunk.document_version_id,
        )
        .where(
            DocumentChunk.document_id == security_scenario.incident_report.id,
            DocumentVersion.version_number
            == security_scenario.incident_report.current_version_number,
        )
    )
    assert authorized_chunk is not None
    authorized_chunk.content = (
        "Critical incidents must be escalated immediately."
    )
    security_scenario.session.flush()

    install_recording_retrieval(
        monkeypatch,
        scenario=security_scenario,
    )
    fake_provider = FakeAnswerProvider(
        GeneratedAnswer(
            answer="Critical incidents must be escalated immediately.",
            answerability=Answerability.ANSWERABLE,
            confidence=0.9,
            citations=[
                CitationDraft(
                    chunk_id=authorized_chunk.id,
                    claims=[
                        "Critical incidents require immediate escalation."
                    ],
                )
            ],
            limitations=[],
        )
    )
    app.dependency_overrides[get_answer_provider] = lambda: fake_provider
    security_scenario.authenticate_as(security_scenario.alice)

    response = security_scenario.client.post(
        f"/organizations/{security_scenario.organization_a.id}/answers",
        json={
            "question": "How should a critical incident be escalated?",
            "workspace_ids": [str(security_scenario.engineering.id)],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == (
        "Critical incidents must be escalated immediately."
    )
    assert payload["answerability"] == Answerability.ANSWERABLE
    assert payload["confidence"] == 0.9
    assert payload["citations"] == [
        {
            "document_id": str(security_scenario.incident_report.id),
            "document_title": security_scenario.incident_report.title,
            "chunk_id": str(authorized_chunk.id),
            "page_number": authorized_chunk.page_number,
            "claims": [
                "Critical incidents require immediate escalation."
            ],
        }
    ]

    answer_run = security_scenario.session.get(
        AnswerRun,
        UUID(payload["answer_run_id"]),
    )
    assert answer_run is not None
    assert answer_run.model_name == fake_provider.model

    citation = security_scenario.session.scalar(
        select(AnswerCitation).where(
            AnswerCitation.answer_run_id == answer_run.id
        )
    )
    assert citation is not None
    assert citation.chunk_id == authorized_chunk.id
