from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.identity.models import User
from app.domains.identity.router import require_user
from app.domains.organizations.service import (
    OrganizationContext,
    OrganizationNotFound,
    OrganizationService,
)

from .schemas import (
    ApplicationListResponse,
    ApplicationResponse,
    CreateApplicationRequest,
    UpdateApplicationRequest,
)
from .service import (
    ApplicationConflict,
    ApplicationNotFound,
    ApplicationService,
    application_response,
)

router = APIRouter(
    prefix="/organizations/{organization_id}/applications",
    tags=["applications"],
)


async def organization_context(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationContext:
    try:
        return await OrganizationService(session).get_context(user.id, organization_id)
    except OrganizationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        ) from exc


@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    search: Annotated[str | None, Query(max_length=120)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> ApplicationListResponse:
    items = await ApplicationService(session).list(context, search=search, status=status_filter)
    return ApplicationListResponse(items=items)


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    body: CreateApplicationRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApplicationResponse:
    try:
        return await ApplicationService(session).create(context, user, body)
    except ApplicationConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApplicationResponse:
    try:
        return application_response(await ApplicationService(session).get(context, application_id))
    except ApplicationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        ) from exc


@router.patch("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: UUID,
    body: UpdateApplicationRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApplicationResponse:
    try:
        return await ApplicationService(session).update(context, application_id, body)
    except ApplicationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        ) from exc


@router.post("/{application_id}/archive", response_model=ApplicationResponse)
async def archive_application(
    application_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApplicationResponse:
    try:
        return await ApplicationService(session).archive(context, application_id)
    except ApplicationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        ) from exc
