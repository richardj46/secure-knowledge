from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.admin.evaluations import (
    AdminEvaluationResourceNotFoundError,
    AdminEvaluationService,
    EvaluationCaseResultAdminDetail,
    EvaluationCaseResultAdminSummary,
    EvaluationCaseReviewAdminRead,
    EvaluationCaseReviewCreate,
    EvaluationRunAdminDetail,
    EvaluationRunAdminSummary,
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
        detail="Evaluation resource not found.",
    ) from exception


@router.get(
    "/evaluation-runs",
    response_model=Page[EvaluationRunAdminSummary],
)
def list_evaluation_runs(
    organization_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> Page[EvaluationRunAdminSummary]:
    try:
        return AdminEvaluationService(session).list_runs(
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
    "/evaluation-runs/{run_id}",
    response_model=EvaluationRunAdminDetail,
)
def get_evaluation_run(
    organization_id: UUID,
    run_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> EvaluationRunAdminDetail:
    try:
        return AdminEvaluationService(session).get_run(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            run_id=run_id,
        )
    except (
        AdminEvaluationResourceNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)


@router.get(
    "/evaluation-runs/{run_id}/cases",
    response_model=Page[EvaluationCaseResultAdminSummary],
)
def list_evaluation_run_cases(
    organization_id: UUID,
    run_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> Page[EvaluationCaseResultAdminSummary]:
    try:
        return AdminEvaluationService(session).list_cases(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            run_id=run_id,
            limit=limit,
            cursor=cursor,
        )
    except (
        AdminEvaluationResourceNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)
    except InvalidAdminCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid pagination cursor.",
        ) from exc


@router.get(
    "/evaluation-case-results/{result_id}",
    response_model=EvaluationCaseResultAdminDetail,
)
def get_evaluation_case_result(
    organization_id: UUID,
    result_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> EvaluationCaseResultAdminDetail:
    try:
        return AdminEvaluationService(session).get_case_result(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            result_id=result_id,
        )
    except (
        AdminEvaluationResourceNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)


@router.post(
    "/evaluation-case-results/{result_id}/reviews",
    response_model=EvaluationCaseReviewAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation_case_review(
    organization_id: UUID,
    result_id: UUID,
    data: EvaluationCaseReviewCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> EvaluationCaseReviewAdminRead:
    try:
        return AdminEvaluationService(session).create_case_review(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            result_id=result_id,
            data=data,
            request_id=request_id_context.get(),
        )
    except (
        AdminEvaluationResourceNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)
