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

from .schemas import (
    ContractBundleResponse,
    ContractListResponse,
    ContractResponse,
    ContractVersionResponse,
    CreateContractRequest,
    RenewalListResponse,
    UpdateContractVersionRequest,
)
from .service import (
    ContractNotFound,
    ContractService,
    ContractVersionNotFound,
    ImmutableContractVersion,
    InvalidContractDates,
)

contracts_router = APIRouter(
    prefix="/organizations/{organization_id}/contracts",
    tags=["contracts"],
)
renewals_router = APIRouter(
    prefix="/organizations/{organization_id}/renewals",
    tags=["contracts"],
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


@contracts_router.post("", response_model=ContractBundleResponse, status_code=201)
async def create_contract(
    body: CreateContractRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ContractBundleResponse:
    return await ContractService(session).create(context, user, body)


@contracts_router.get("", response_model=ContractListResponse)
async def list_contracts(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ContractListResponse:
    return await ContractService(session).list(context)


@contracts_router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ContractResponse:
    try:
        return await ContractService(session).get_response(context, contract_id)
    except ContractNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        ) from exc


@contracts_router.patch(
    "/{contract_id}/versions/{version_id}",
    response_model=ContractVersionResponse,
)
async def update_contract_version(
    contract_id: UUID,
    version_id: UUID,
    body: UpdateContractVersionRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ContractVersionResponse:
    try:
        return await ContractService(session).update_version(
            context,
            contract_id,
            version_id,
            body,
        )
    except (ContractNotFound, ContractVersionNotFound) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract version not found",
        ) from exc
    except ImmutableContractVersion as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Signed contract versions are immutable",
        ) from exc
    except InvalidContractDates as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Contract end date must be after start date",
        ) from exc


@contracts_router.post(
    "/{contract_id}/versions/{version_id}/mark-signed",
    response_model=ContractBundleResponse,
)
async def mark_contract_version_signed(
    contract_id: UUID,
    version_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ContractBundleResponse:
    try:
        return await ContractService(session).mark_signed(context, contract_id, version_id)
    except (ContractNotFound, ContractVersionNotFound) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract version not found",
        ) from exc


@renewals_router.get("", response_model=RenewalListResponse)
async def list_renewals(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RenewalListResponse:
    return await ContractService(session).list_renewals(context)
