from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import get_session
from app.domains.identity.models import User
from app.domains.identity.router import require_user
from app.domains.organizations.service import (
    OrganizationContext,
    OrganizationNotFound,
    OrganizationService,
)

from .handler import (
    BillingEventHandler,
    BillingObjectNotFound,
    InvalidBillingEvent,
    UnsupportedBillingEvent,
)
from .management import BillingManagementService
from .plan_changes import PlanChangeNotAllowed, PlanChangeService
from .provider import InvalidBillingWebhook, build_billing_provider
from .schemas import (
    BillingInvoiceListResponse,
    BillingPlanListResponse,
    BillingSummaryResponse,
    BillingUsageResponse,
    BillingWebhookResponse,
    PlanChangePreviewResponse,
    PlanChangeRequest,
    PortalSessionRequest,
    PortalSessionResponse,
)

webhook_router = APIRouter(
    prefix="/billing/webhooks",
    tags=["billing-webhooks"],
)
public_router = APIRouter(prefix="/billing", tags=["billing"])
management_router = APIRouter(
    prefix="/organizations/{organization_id}/billing",
    tags=["billing"],
)


async def billing_context(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationContext:
    try:
        context = await OrganizationService(session).get_context(
            user.id,
            organization_id,
        )
    except OrganizationNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc
    if context.role not in {"owner", "admin", "finance", "finance_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Billing administration is forbidden",
        )
    return context


@public_router.get("/plans", response_model=BillingPlanListResponse)
async def list_billing_plans(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BillingPlanListResponse:
    response = await BillingManagementService(session).list_plans()
    await session.commit()
    return response


@management_router.get("", response_model=BillingSummaryResponse)
async def get_billing_summary(
    context: Annotated[OrganizationContext, Depends(billing_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BillingSummaryResponse:
    response = await BillingManagementService(session).summary(
        context.organization_id
    )
    await session.commit()
    return response


@management_router.get("/usage", response_model=BillingUsageResponse)
async def get_billing_usage(
    context: Annotated[OrganizationContext, Depends(billing_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BillingUsageResponse:
    return await BillingManagementService(session).usage(context.organization_id)


@management_router.get("/invoices", response_model=BillingInvoiceListResponse)
async def list_billing_invoices(
    context: Annotated[OrganizationContext, Depends(billing_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BillingInvoiceListResponse:
    return await BillingManagementService(session).invoices(context.organization_id)


@management_router.post(
    "/change-preview",
    response_model=PlanChangePreviewResponse,
)
async def preview_plan_change(
    body: PlanChangeRequest,
    context: Annotated[OrganizationContext, Depends(billing_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PlanChangePreviewResponse:
    try:
        preview = await PlanChangeService(session).preview_change(
            context.organization_id,
            target_plan=body.target_plan,
        )
    except PlanChangeNotAllowed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return PlanChangePreviewResponse(**preview.__dict__)


@management_router.post("/change-plan", response_model=BillingSummaryResponse)
async def change_plan(
    body: PlanChangeRequest,
    context: Annotated[OrganizationContext, Depends(billing_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BillingSummaryResponse:
    service = PlanChangeService(session)
    try:
        await service.change_plan(
            context.organization_id,
            target_plan=body.target_plan,
        )
    except PlanChangeNotAllowed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return await BillingManagementService(session).summary(context.organization_id)


@management_router.post("/cancel", response_model=BillingSummaryResponse)
async def cancel_subscription(
    context: Annotated[OrganizationContext, Depends(billing_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BillingSummaryResponse:
    try:
        await PlanChangeService(session).cancel_at_period_end(
            context.organization_id
        )
    except PlanChangeNotAllowed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return await BillingManagementService(session).summary(context.organization_id)


@management_router.post(
    "/undo-cancellation",
    response_model=BillingSummaryResponse,
)
async def undo_cancellation(
    context: Annotated[OrganizationContext, Depends(billing_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BillingSummaryResponse:
    try:
        await PlanChangeService(session).undo_cancellation(
            context.organization_id
        )
    except PlanChangeNotAllowed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return await BillingManagementService(session).summary(context.organization_id)


@management_router.post(
    "/portal-session",
    response_model=PortalSessionResponse,
)
async def create_portal_session(
    body: PortalSessionRequest,
    context: Annotated[OrganizationContext, Depends(billing_context)],
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PortalSessionResponse:
    url = await BillingManagementService(session).portal_session(
        context.organization_id,
        user=user,
        provider_name=settings.billing_provider,
        provider=build_billing_provider(settings),
        return_url=body.return_url,
    )
    await session.commit()
    return PortalSessionResponse(url=url)


@webhook_router.post(
    "/{provider_name}",
    response_model=BillingWebhookResponse,
)
async def process_billing_webhook(
    provider_name: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BillingWebhookResponse:
    if provider_name != settings.billing_provider:
        raise HTTPException(status_code=404, detail="Billing provider not found")
    provider = build_billing_provider(settings)
    try:
        event = provider.verify_webhook(request.headers, await request.body())
        result = await BillingEventHandler(session, provider_name).handle(event)
    except InvalidBillingWebhook as exc:
        raise HTTPException(status_code=400, detail="Invalid billing webhook") from exc
    except UnsupportedBillingEvent as exc:
        raise HTTPException(status_code=422, detail="Unsupported billing event") from exc
    except (BillingObjectNotFound, InvalidBillingEvent) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return BillingWebhookResponse(
        accepted=True,
        duplicate=result.duplicate,
        stale=result.stale,
        event_id=result.event_id,
    )
