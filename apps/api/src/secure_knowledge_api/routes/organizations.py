from fastapi import APIRouter, HTTPException, status
from secure_knowledge_core.organizations.schemas import (
    OrganizationCreate,
    OrganizationRead,
)
from secure_knowledge_core.organizations.service import (
    OrganizationService,
    OrganizationSlugAlreadyExistsError,
)

from secure_knowledge_api.dependencies.auth import CurrentUser
from secure_knowledge_api.dependencies.database import DatabaseSession

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    data: OrganizationCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> OrganizationRead:
    service = OrganizationService(session)

    try:
        organization = service.create_organization(
            owner_user_id=current_user.id,
            data=data,
        )
    except OrganizationSlugAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already exists.",
        ) from exc

    return OrganizationRead.model_validate(organization)


@router.get("", response_model=list[OrganizationRead])
def list_organizations(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[OrganizationRead]:
    service = OrganizationService(session)
    organizations = service.list_for_user(current_user.id)

    return [OrganizationRead.model_validate(organization) for organization in organizations]
