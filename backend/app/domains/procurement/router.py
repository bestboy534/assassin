from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
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
    ApprovalTaskListResponse,
    ApprovalTaskResponse,
    ApproveTaskRequest,
    CreatePurchaseRequest,
    PurchaseRequestListResponse,
    PurchaseRequestResponse,
)
from .service import (
    ApprovalTaskNotFound,
    ProcurementService,
    PurchaseRequestNotFound,
)

purchase_requests_router = APIRouter(
    prefix="/organizations/{organization_id}/purchase-requests",
    tags=["procurement"],
)

approval_tasks_router = APIRouter(
    prefix="/organizations/{organization_id}/approval-tasks",
    tags=["procurement"],
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


@purchase_requests_router.post("", response_model=PurchaseRequestResponse, status_code=201)
async def create_purchase_request(
    body: CreatePurchaseRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PurchaseRequestResponse:
    return await ProcurementService(session).create_request(context, user, body)


@purchase_requests_router.get("", response_model=PurchaseRequestListResponse)
async def list_purchase_requests(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    search: Annotated[str | None, Query(max_length=120)] = None,
) -> PurchaseRequestListResponse:
    _ = search
    return await ProcurementService(session).list_requests(context)


@purchase_requests_router.get("/{request_id}", response_model=PurchaseRequestResponse)
async def get_purchase_request(
    request_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PurchaseRequestResponse:
    try:
        return await ProcurementService(session).get_request_response(context, request_id)
    except PurchaseRequestNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase request not found",
        ) from exc


@purchase_requests_router.post("/{request_id}/submit", response_model=PurchaseRequestResponse)
async def submit_purchase_request(
    request_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PurchaseRequestResponse:
    try:
        return await ProcurementService(session).submit_request(context, request_id)
    except PurchaseRequestNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase request not found",
        ) from exc


@approval_tasks_router.get("", response_model=ApprovalTaskListResponse)
async def list_approval_tasks(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApprovalTaskListResponse:
    return await ProcurementService(session).list_tasks(context)


@approval_tasks_router.post("/{task_id}/approve", response_model=ApprovalTaskResponse)
async def approve_task(
    task_id: UUID,
    body: ApproveTaskRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ApprovalTaskResponse:
    try:
        return await ProcurementService(session).approve_task(
            context,
            task_id,
            user,
            body,
            idempotency_key,
        )
    except ApprovalTaskNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval task not found",
        ) from exc
