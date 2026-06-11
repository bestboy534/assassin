from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.identity.models import User
from app.domains.identity.router import require_user

from .schemas import CreateOrganizationRequest, OrganizationListResponse, OrganizationResponse
from .service import OrganizationNotFound, OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationListResponse:
    return OrganizationListResponse(items=await OrganizationService(session).list_for_user(user.id))


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: CreateOrganizationRequest,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationResponse:
    return await OrganizationService(session).create(user, body.name)


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationResponse:
    service = OrganizationService(session)
    try:
        context = await service.get_context(user.id, organization_id)
    except OrganizationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        ) from exc
    organizations = await service.list_for_user(user.id)
    for organization in organizations:
        if organization.id == context.organization_id:
            return organization
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
