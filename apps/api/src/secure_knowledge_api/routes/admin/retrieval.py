from datetime import datetime
from typing import Annotated, Never
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession
from secure_knowledge_core.admin.pagination import (
    InvalidAdminCursorError,
    Page,
)
from secure_knowledge_core.admin.retrieval import (
    AdminRetrievalRunNotFoundError,
    AdminRetrievalService,
    RetrievalRunDetail,
    RetrievalTraceResultRead,
)
from secure_knowledge_core.authorization.exceptions import (
    OrganizationAccessDeniedError,
)

router = APIRouter(
    prefix="/organizations/{organization_id}/admin",
    tags=["admin"],
)


def _raise_not_found(exception: Exception) -> Never:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Retrieval run not found.",
    ) from exception


@router.get(
    "/retrieval-runs",
    response_model=Page[RetrievalRunDetail],
)
def list_retrieval_runs(
    organization_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    user_id: Annotated[UUID | None, Query()] = None,
    workspace_id: Annotated[UUID | None, Query()] = None,
    document_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    empty_results: Annotated[bool | None, Query()] = None,
    minimum_duration_ms: Annotated[int | None, Query(ge=0)] = None,
    query: Annotated[str | None, Query(max_length=2000)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> Page[RetrievalRunDetail]:
    try:
        return AdminRetrievalService(session).list_runs(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            user_id=user_id,
            workspace_id=workspace_id,
            document_id=document_id,
            date_from=date_from,
            date_to=date_to,
            empty_results=empty_results,
            minimum_duration_ms=minimum_duration_ms,
            query=query,
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
    "/retrieval-runs/{run_id}",
    response_model=RetrievalRunDetail,
)
def get_retrieval_run(
    organization_id: UUID,
    run_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> RetrievalRunDetail:
    try:
        return AdminRetrievalService(session).get_run(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            run_id=run_id,
        )
    except (
        AdminRetrievalRunNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)


@router.get(
    "/retrieval-runs/{run_id}/results",
    response_model=Page[RetrievalTraceResultRead],
)
def list_retrieval_run_results(
    organization_id: UUID,
    run_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
) -> Page[RetrievalTraceResultRead]:
    try:
        return AdminRetrievalService(session).list_results(
            organization_id=organization_id,
            actor_user_id=current_user.id,
            run_id=run_id,
            limit=limit,
            cursor=cursor,
        )
    except (
        AdminRetrievalRunNotFoundError,
        OrganizationAccessDeniedError,
    ) as exc:
        _raise_not_found(exc)
    except InvalidAdminCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid pagination cursor.",
        ) from exc
