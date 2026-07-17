from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.admin.answers import (
    AdminAnswerRunNotFoundError,
    AdminAnswerService,
    AnswerCitationInspection,
    AnswerReviewCreate,
    AnswerReviewRead,
    AnswerRunDetail,
    AnswerRunSummary,
)
from secure_knowledge_core.admin.pagination import (
    InvalidAdminCursorError,
    Page,
)
from secure_knowledge_core.authorization.exceptions import (
    OrganizationAccessDeniedError,
)
from secure_knowledge_core.core.logging import request_id_context

router = APIRouter(
    prefix="/organizations/{organization_id}/admin",
    tags=["admin"],
)


def _raise_not_found(exception: Exception) -> Never:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Answer run not found.",
    ) from exception


@router.get(
    "/answer-runs",
    response_model=Page[AnswerRunSummary],
)
def list_answer_runs(
    organization_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> Page[AnswerRunSummary]:
    try:
        return AdminAnswerService(session).list_runs(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            limit=limit,
            cursor=cursor,
        )
    except OrganizationAccessDeniedError as exc:
        _raise_not_found(exc)
    except InvalidAdminCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid pagination cursor.",
        ) from exc


@router.get(
    "/answer-runs/{answer_run_id}",
    response_model=AnswerRunDetail,
)
def get_answer_run(
    organization_id: UUID,
    answer_run_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> AnswerRunDetail:
    try:
        return AdminAnswerService(session).get_run(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            answer_run_id=answer_run_id,
        )
    except (
        AdminAnswerRunNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)


@router.get(
    "/answer-runs/{answer_run_id}/citations",
    response_model=Page[AnswerCitationInspection],
)
def list_answer_run_citations(
    organization_id: UUID,
    answer_run_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> Page[AnswerCitationInspection]:
    try:
        return AdminAnswerService(session).list_citations(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            answer_run_id=answer_run_id,
            limit=limit,
            cursor=cursor,
        )
    except (
        AdminAnswerRunNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)
    except InvalidAdminCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid pagination cursor.",
        ) from exc


@router.post(
    "/answer-runs/{answer_run_id}/reviews",
    response_model=AnswerReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def create_answer_run_review(
    organization_id: UUID,
    answer_run_id: UUID,
    data: AnswerReviewCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> AnswerReviewRead:
    try:
        return AdminAnswerService(session).create_review(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            answer_run_id=answer_run_id,
            data=data,
            request_id=request_id_context.get(),
        )
    except (
        AdminAnswerRunNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)
