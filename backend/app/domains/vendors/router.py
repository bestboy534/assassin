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
    AcceptRiskFindingRequest,
    CreateVendorAliasRequest,
    CreateVendorAssessmentRequest,
    CreateVendorRequest,
    LatestVendorAssessmentResponse,
    RiskFindingListResponse,
    RiskFindingResponse,
    VendorAliasResponse,
    VendorAssessmentBundleResponse,
    VendorListResponse,
    VendorResponse,
)
from .service import (
    RiskAcceptanceForbidden,
    RiskFindingNotFound,
    VendorConflict,
    VendorNotFound,
    VendorService,
)

vendors_router = APIRouter(
    prefix="/organizations/{organization_id}/vendors",
    tags=["vendors"],
)
risk_findings_router = APIRouter(
    prefix="/organizations/{organization_id}/risk-findings",
    tags=["vendors"],
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


@vendors_router.post("", response_model=VendorResponse, status_code=201)
async def create_vendor(
    body: CreateVendorRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VendorResponse:
    try:
        return await VendorService(session).create(context, user, body)
    except VendorConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vendor or alias already exists",
        ) from exc


@vendors_router.get("", response_model=VendorListResponse)
async def list_vendors(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VendorListResponse:
    return await VendorService(session).list(context)


@vendors_router.get("/match", response_model=VendorResponse)
async def match_vendor(
    name: Annotated[str, Query(min_length=1, max_length=255)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VendorResponse:
    try:
        return await VendorService(session).match(context, name)
    except VendorNotFound as exc:
        raise HTTPException(status_code=404, detail="Vendor not found") from exc


@vendors_router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VendorResponse:
    try:
        return await VendorService(session).get_response(context, vendor_id)
    except VendorNotFound as exc:
        raise HTTPException(status_code=404, detail="Vendor not found") from exc


@vendors_router.post(
    "/{vendor_id}/aliases",
    response_model=VendorAliasResponse,
    status_code=201,
)
async def add_vendor_alias(
    vendor_id: UUID,
    body: CreateVendorAliasRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VendorAliasResponse:
    try:
        return await VendorService(session).add_alias(context, vendor_id, body.alias)
    except VendorNotFound as exc:
        raise HTTPException(status_code=404, detail="Vendor not found") from exc
    except VendorConflict as exc:
        raise HTTPException(status_code=409, detail="Vendor alias already exists") from exc


@vendors_router.post("/{vendor_id}/archive", response_model=VendorResponse)
async def archive_vendor(
    vendor_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VendorResponse:
    try:
        return await VendorService(session).archive(context, vendor_id)
    except VendorNotFound as exc:
        raise HTTPException(status_code=404, detail="Vendor not found") from exc


@vendors_router.post(
    "/{vendor_id}/assessments",
    response_model=VendorAssessmentBundleResponse,
    status_code=201,
)
async def assess_vendor(
    vendor_id: UUID,
    body: CreateVendorAssessmentRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VendorAssessmentBundleResponse:
    try:
        return await VendorService(session).assess(context, user, vendor_id, body)
    except VendorNotFound as exc:
        raise HTTPException(status_code=404, detail="Vendor not found") from exc


@vendors_router.get(
    "/{vendor_id}/assessments/latest",
    response_model=LatestVendorAssessmentResponse,
)
async def latest_vendor_assessment(
    vendor_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LatestVendorAssessmentResponse:
    try:
        return await VendorService(session).latest_assessment(context, vendor_id)
    except VendorNotFound as exc:
        raise HTTPException(status_code=404, detail="Vendor not found") from exc


@risk_findings_router.get("", response_model=RiskFindingListResponse)
async def list_risk_findings(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RiskFindingListResponse:
    return await VendorService(session).list_findings(context)


@risk_findings_router.post("/{finding_id}/accept", response_model=RiskFindingResponse)
async def accept_risk_finding(
    finding_id: UUID,
    body: AcceptRiskFindingRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RiskFindingResponse:
    try:
        return await VendorService(session).accept_finding(context, user, finding_id, body)
    except RiskAcceptanceForbidden as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners or security administrators can accept risk",
        ) from exc
    except RiskFindingNotFound as exc:
        raise HTTPException(status_code=404, detail="Risk finding not found") from exc
