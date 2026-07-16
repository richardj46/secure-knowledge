from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from secure_knowledge_api.dependencies.answers import (
    AnswerServiceDependency,
)
from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_core.answers.exceptions import (
    AnswerGenerationFailedError,
    CitationValidationError,
    ConversationAccessDeniedError,
)
from secure_knowledge_core.answers.schemas import (
    AnswerRequest,
    AnswerResponse,
)
from secure_knowledge_core.retrieval.exceptions import OrganizationNotFoundError

router = APIRouter(tags=["answers"])


@router.post(
    "/organizations/{organization_id}/answers",
    response_model=AnswerResponse,
)
def answer_question(
    organization_id: UUID,
    data: AnswerRequest,
    current_user: CurrentUser,
    service: AnswerServiceDependency,
) -> AnswerResponse:
    try:
        return service.answer(
            organization_id=organization_id,
            user_id=current_user.id,
            request=data,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        ) from exc
    except ConversationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        ) from exc
    except CitationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The answer provider returned invalid citations.",
        ) from exc
    except AnswerGenerationFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Answer generation is temporarily unavailable.",
        ) from exc
