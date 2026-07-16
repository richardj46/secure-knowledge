from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.retrieval.exceptions import (
    OrganizationNotFoundError,
    RetrievalUnavailableError,
    WorkspaceFilterNotFoundError,
)
from secure_knowledge_core.retrieval.schemas import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from secure_knowledge_core.retrieval.service import RetrievalService

router = APIRouter(tags=["retrieval"])


@router.post(
    "/organizations/{organization_id}/retrieval/search",
    response_model=RetrievalSearchResponse,
)
def search(
    organization_id: UUID,
    data: RetrievalSearchRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> RetrievalSearchResponse:
    try:
        service = RetrievalService(session)
        return service.search(
            organization_id=organization_id,
            user_id=current_user.id,
            request=data,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Organization not found.",
        ) from exc
    except WorkspaceFilterNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Workspace not found.",
        ) from exc
    except RetrievalUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Retrieval is temporarily unavailable.",
        ) from exc
