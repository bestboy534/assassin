from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
    CreateOptimizationProjectRequest,
    CreateSavingsOpportunityRequest,
    OptimizationProjectBundleResponse,
    OptimizationProjectListResponse,
    RealizeSavingsRequest,
    SavingsOpportunityListResponse,
    SavingsOpportunityResponse,
    SavingsSummaryResponse,
    VerifySavingsRequest,
)
from .service import (
    InvalidSavingsTransition,
    OptimizationProjectNotFound,
    SavingsOpportunityNotFound,
    SavingsService,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["savings"])


async def organization_context(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationContext:
    try:
        return await OrganizationService(session).get_context(user.id, organization_id)
    except OrganizationNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc


@router.post(
    "/savings-opportunities",
    response_model=SavingsOpportunityResponse,
    status_code=201,
)
async def create_savings_opportunity(
    body: CreateSavingsOpportunityRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SavingsOpportunityResponse:
    return await SavingsService(session).create_opportunity(context, body)


@router.get(
    "/savings-opportunities",
    response_model=SavingsOpportunityListResponse,
)
async def list_savings_opportunities(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SavingsOpportunityListResponse:
    return await SavingsService(session).list_opportunities(context)


@router.post(
    "/savings-opportunities/{opportunity_id}/confirm",
    response_model=SavingsOpportunityResponse,
)
async def confirm_savings_opportunity(
    opportunity_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SavingsOpportunityResponse:
    try:
        return await SavingsService(session).confirm(context, opportunity_id)
    except SavingsOpportunityNotFound as exc:
        raise HTTPException(status_code=404, detail="Savings opportunity not found") from exc
    except InvalidSavingsTransition as exc:
        raise HTTPException(status_code=409, detail="Invalid savings transition") from exc


@router.post(
    "/savings-opportunities/{opportunity_id}/projects",
    response_model=OptimizationProjectBundleResponse,
    status_code=201,
)
async def create_optimization_project(
    opportunity_id: UUID,
    body: CreateOptimizationProjectRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OptimizationProjectBundleResponse:
    try:
        return await SavingsService(session).create_project(context, opportunity_id, body)
    except SavingsOpportunityNotFound as exc:
        raise HTTPException(status_code=404, detail="Savings opportunity not found") from exc
    except InvalidSavingsTransition as exc:
        raise HTTPException(status_code=409, detail="Confirm the opportunity first") from exc


@router.post(
    "/optimization-projects/{project_id}/realize",
    response_model=OptimizationProjectBundleResponse,
)
async def realize_savings(
    project_id: UUID,
    body: RealizeSavingsRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OptimizationProjectBundleResponse:
    try:
        return await SavingsService(session).realize(context, project_id, body)
    except OptimizationProjectNotFound as exc:
        raise HTTPException(status_code=404, detail="Optimization project not found") from exc


@router.get(
    "/optimization-projects",
    response_model=OptimizationProjectListResponse,
)
async def list_optimization_projects(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OptimizationProjectListResponse:
    return await SavingsService(session).list_projects(context)


@router.post(
    "/optimization-projects/{project_id}/verify",
    response_model=OptimizationProjectBundleResponse,
)
async def verify_savings(
    project_id: UUID,
    body: VerifySavingsRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OptimizationProjectBundleResponse:
    try:
        return await SavingsService(session).verify(context, project_id, body)
    except OptimizationProjectNotFound as exc:
        raise HTTPException(status_code=404, detail="Optimization project not found") from exc
    except InvalidSavingsTransition as exc:
        raise HTTPException(status_code=409, detail="Realize savings before verification") from exc


@router.get("/savings-summary", response_model=SavingsSummaryResponse)
async def get_savings_summary(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SavingsSummaryResponse:
    return await SavingsService(session).summary(context)
