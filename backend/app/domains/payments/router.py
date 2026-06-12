from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
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

from .provider import InvalidPaymentWebhook, build_payment_provider
from .schemas import (
    CreatePaymentInstrumentRequest,
    PaymentInstrumentBundleResponse,
    PaymentInstrumentListResponse,
    PaymentLimitsRequest,
    PaymentWebhookResponse,
)
from .service import (
    InvalidPaymentTransition,
    PaymentInstrumentNotFound,
    PaymentRequestConflict,
    PaymentService,
    PurchaseNotApproved,
    bundle_response,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["payments"])
webhook_router = APIRouter(prefix="/webhooks/payments", tags=["payment-webhooks"])


async def organization_context(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationContext:
    try:
        return await OrganizationService(session).get_context(user.id, organization_id)
    except OrganizationNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc


def payment_service(
    session: AsyncSession,
    settings: Settings,
) -> PaymentService:
    return PaymentService(
        session,
        build_payment_provider(settings),
        settings.payment_provider,
    )


@router.post(
    "/payment-instruments",
    response_model=PaymentInstrumentBundleResponse,
    status_code=201,
)
async def create_payment_instrument(
    body: CreatePaymentInstrumentRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
) -> PaymentInstrumentBundleResponse:
    try:
        return await payment_service(session, settings).create_instrument(
            context,
            user,
            body,
            idempotency_key,
        )
    except PurchaseNotApproved as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Purchase request must be approved before creating a payment instrument",
        ) from exc
    except PaymentRequestConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment instrument creation is already in progress",
        ) from exc


@router.get(
    "/payment-instruments",
    response_model=PaymentInstrumentListResponse,
)
async def list_payment_instruments(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentInstrumentListResponse:
    return await payment_service(session, settings).list_instruments(context)


@router.get(
    "/payment-instruments/{instrument_id}",
    response_model=PaymentInstrumentBundleResponse,
)
async def get_payment_instrument(
    instrument_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentInstrumentBundleResponse:
    try:
        item = await payment_service(session, settings).get_instrument(
            context,
            instrument_id,
        )
        return bundle_response(item)
    except PaymentInstrumentNotFound as exc:
        raise HTTPException(status_code=404, detail="Payment instrument not found") from exc


@router.put(
    "/payment-instruments/{instrument_id}/limits",
    response_model=PaymentInstrumentBundleResponse,
)
async def update_payment_limits(
    instrument_id: UUID,
    body: PaymentLimitsRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentInstrumentBundleResponse:
    try:
        return await payment_service(session, settings).update_limits(
            context,
            user,
            instrument_id,
            body,
        )
    except PaymentInstrumentNotFound as exc:
        raise HTTPException(status_code=404, detail="Payment instrument not found") from exc
    except InvalidPaymentTransition as exc:
        raise HTTPException(status_code=409, detail="Invalid payment transition") from exc


async def lifecycle_action(
    action: str,
    instrument_id: UUID,
    context: OrganizationContext,
    user: User,
    session: AsyncSession,
    settings: Settings,
) -> PaymentInstrumentBundleResponse:
    service = payment_service(session, settings)
    try:
        if action == "freeze":
            return await service.freeze(context, user, instrument_id)
        if action == "unfreeze":
            return await service.unfreeze(context, user, instrument_id)
        return await service.close(context, user, instrument_id)
    except PaymentInstrumentNotFound as exc:
        raise HTTPException(status_code=404, detail="Payment instrument not found") from exc
    except InvalidPaymentTransition as exc:
        raise HTTPException(status_code=409, detail="Invalid payment transition") from exc


@router.post(
    "/payment-instruments/{instrument_id}/freeze",
    response_model=PaymentInstrumentBundleResponse,
)
async def freeze_payment_instrument(
    instrument_id: UUID,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentInstrumentBundleResponse:
    return await lifecycle_action(
        "freeze",
        instrument_id,
        context,
        user,
        session,
        settings,
    )


@router.post(
    "/payment-instruments/{instrument_id}/unfreeze",
    response_model=PaymentInstrumentBundleResponse,
)
async def unfreeze_payment_instrument(
    instrument_id: UUID,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentInstrumentBundleResponse:
    return await lifecycle_action(
        "unfreeze",
        instrument_id,
        context,
        user,
        session,
        settings,
    )


@router.post(
    "/payment-instruments/{instrument_id}/close",
    response_model=PaymentInstrumentBundleResponse,
)
async def close_payment_instrument(
    instrument_id: UUID,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentInstrumentBundleResponse:
    return await lifecycle_action(
        "close",
        instrument_id,
        context,
        user,
        session,
        settings,
    )


@webhook_router.post(
    "/{provider_name}",
    response_model=PaymentWebhookResponse,
)
async def process_payment_webhook(
    provider_name: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentWebhookResponse:
    if provider_name != settings.payment_provider:
        raise HTTPException(status_code=404, detail="Payment provider not found")
    provider = build_payment_provider(settings)
    body = await request.body()
    try:
        event = provider.verify_webhook(request.headers, body)
        return await PaymentService(
            session,
            provider,
            settings.payment_provider,
        ).process_event(event)
    except InvalidPaymentWebhook as exc:
        raise HTTPException(status_code=400, detail="Invalid payment webhook") from exc
    except PaymentInstrumentNotFound as exc:
        raise HTTPException(status_code=404, detail="Payment instrument not found") from exc
