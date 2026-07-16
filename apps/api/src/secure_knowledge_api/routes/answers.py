from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.answers.exceptions import (
    ConversationNotFoundError,
    RetrievalTraceMissingError,
)
from secure_knowledge_core.answers.schemas import AnswerRequest, AnswerResponse
from secure_knowledge_core.answers.service import AnswerService
from secure_knowledge_core.llm.exceptions import (
    AnswerProviderError,
    CitationValidationError,
)
from secure_knowledge_core.retrieval.exceptions import (
    OrganizationNotFoundError,
    RetrievalUnavailableError,
    WorkspaceFilterNotFoundError,
)

router = APIRouter(tags=["answers"])


@router.post(
    "/organizations/{organization_id}/answers",
    response_model=AnswerResponse,
)
def answer_question(
    organization_id: UUID,
    data: AnswerRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> AnswerResponse:
    try:
        return AnswerService(session).answer(
            organization_id=organization_id,
            user_id=current_user.id,
            conversation_id=data.conversation_id,
            question=data.question,
            workspace_ids=data.workspace_ids,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Organization not found.",
        ) from exc
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Conversation not found.",
        ) from exc
    except WorkspaceFilterNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Workspace not found.",
        ) from exc
    except (RetrievalUnavailableError, RetrievalTraceMissingError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Answer retrieval is temporarily unavailable.",
        ) from exc
    except CitationValidationError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Answer generation returned invalid citations.",
        ) from exc
    except AnswerProviderError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Answer generation is temporarily unavailable.",
        ) from exc
