from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.identity.models import User
from app.domains.identity.router import require_user
from app.domains.organizations.service import (
    OrganizationContext,
    OrganizationNotFound,
    OrganizationService,
)

from .schemas import AnalysisRunDetailResponse, AnalysisRunListResponse, CreateAnalysisRunRequest
from .service import AnalysisRunNotFound, BillingAuditService

router = APIRouter(
    prefix="/organizations/{organization_id}/analysis-runs",
    tags=["billing-audit"],
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


@router.post(
    "",
    response_model=AnalysisRunDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_analysis_run(
    body: CreateAnalysisRunRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnalysisRunDetailResponse:
    return await BillingAuditService(session).create_from_text(context, user, body)


@router.get("", response_model=AnalysisRunListResponse)
async def list_analysis_runs(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnalysisRunListResponse:
    return await BillingAuditService(session).list(context)


@router.get("/{run_id}", response_model=AnalysisRunDetailResponse)
async def get_analysis_run(
    run_id: str,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnalysisRunDetailResponse:
    try:
        return await BillingAuditService(session).get(context, run_id)
    except AnalysisRunNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis run not found",
        ) from exc
