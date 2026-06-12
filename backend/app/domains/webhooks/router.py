from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import get_session
from app.domains.compliance.router import organization_context
from app.domains.organizations.service import OrganizationContext
from app.infrastructure.secrets import LocalSecretCipher, SecretCipher

from .delivery import HttpxWebhookSender, WebhookDeliveryService, WebhookSender
from .models import WebhookDelivery
from .schemas import (
    CreateWebhookEndpointRequest,
    RotateWebhookSecretRequest,
    TestWebhookRequest,
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
    WebhookEndpointCreatedResponse,
    WebhookEndpointListResponse,
    WebhookSecretRotatedResponse,
)
from .service import (
    WebhookAccessForbidden,
    WebhookDeliveryNotFound,
    WebhookEndpointNotFound,
    WebhookService,
)

router = APIRouter(
    prefix="/organizations/{organization_id}/webhooks",
    tags=["webhooks"],
)


def webhook_sender_from_request(request: Request) -> WebhookSender:
    sender = getattr(request.app.state, "webhook_sender", None)
    return cast(WebhookSender, sender) if sender is not None else HttpxWebhookSender()


def webhook_cipher(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SecretCipher:
    return LocalSecretCipher(settings.webhook_secret_key.get_secret_value())


@router.post("", response_model=WebhookEndpointCreatedResponse, status_code=201)
async def create_webhook_endpoint(
    body: CreateWebhookEndpointRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    cipher: Annotated[SecretCipher, Depends(webhook_cipher)],
) -> WebhookEndpointCreatedResponse:
    try:
        endpoint, secret = await WebhookService(session, cipher).create_for_context(
            context,
            name=body.name,
            url=body.url,
            events=body.events,
        )
    except WebhookAccessForbidden as exc:
        raise HTTPException(status_code=403, detail="Webhook administration is forbidden") from exc
    return WebhookEndpointCreatedResponse(**endpoint.model_dump(), secret=secret)


@router.get("", response_model=WebhookEndpointListResponse)
async def list_webhook_endpoints(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    cipher: Annotated[SecretCipher, Depends(webhook_cipher)],
) -> WebhookEndpointListResponse:
    try:
        return WebhookEndpointListResponse(
            items=await WebhookService(session, cipher).list_endpoints(context)
        )
    except WebhookAccessForbidden as exc:
        raise HTTPException(status_code=403, detail="Webhook administration is forbidden") from exc


@router.post(
    "/{endpoint_id}/rotate-secret",
    response_model=WebhookSecretRotatedResponse,
)
async def rotate_webhook_secret(
    endpoint_id: UUID,
    body: RotateWebhookSecretRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    cipher: Annotated[SecretCipher, Depends(webhook_cipher)],
) -> WebhookSecretRotatedResponse:
    try:
        endpoint, secret = await WebhookService(session, cipher).rotate_secret(
            context,
            endpoint_id,
            overlap_seconds=body.overlap_seconds,
        )
    except WebhookAccessForbidden as exc:
        raise HTTPException(status_code=403, detail="Webhook administration is forbidden") from exc
    except WebhookEndpointNotFound as exc:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found") from exc
    assert endpoint.previous_secret_expires_at is not None
    return WebhookSecretRotatedResponse(
        id=endpoint.id,
        secret=secret,
        secret_version=endpoint.secret_version,
        previous_secret_expires_at=endpoint.previous_secret_expires_at,
    )


@router.post(
    "/{endpoint_id}/test",
    response_model=WebhookDeliveryResponse,
    status_code=201,
)
async def test_webhook_endpoint(
    endpoint_id: UUID,
    body: TestWebhookRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    cipher: Annotated[SecretCipher, Depends(webhook_cipher)],
    sender: Annotated[WebhookSender, Depends(webhook_sender_from_request)],
) -> WebhookDeliveryResponse:
    service = WebhookService(session, cipher)
    try:
        service.require_admin(context)
        await service.get_endpoint(context.organization_id, endpoint_id)
        deliveries = await service.publish_event(
            organization_id=context.organization_id,
            endpoint_id=endpoint_id,
            event_id=uuid4(),
            event_type=body.event_type,
            payload=body.payload,
        )
    except WebhookAccessForbidden as exc:
        raise HTTPException(status_code=403, detail="Webhook administration is forbidden") from exc
    except WebhookEndpointNotFound as exc:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found") from exc
    if not deliveries:
        raise HTTPException(
            status_code=422,
            detail="Endpoint is inactive or not subscribed to this event",
        )
    delivery = await WebhookDeliveryService(session, cipher, sender).deliver(
        context.organization_id,
        endpoint_id,
        deliveries[0].id,
    )
    return delivery_response(delivery)


@router.get(
    "/{endpoint_id}/deliveries",
    response_model=WebhookDeliveryListResponse,
)
async def list_webhook_deliveries(
    endpoint_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    cipher: Annotated[SecretCipher, Depends(webhook_cipher)],
) -> WebhookDeliveryListResponse:
    try:
        deliveries = await WebhookService(session, cipher).list_deliveries(
            context,
            endpoint_id,
        )
    except WebhookAccessForbidden as exc:
        raise HTTPException(status_code=403, detail="Webhook administration is forbidden") from exc
    except WebhookEndpointNotFound as exc:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found") from exc
    return WebhookDeliveryListResponse(
        items=[delivery_response(delivery) for delivery in deliveries]
    )


@router.post(
    "/{endpoint_id}/deliveries/{delivery_id}/retry",
    response_model=WebhookDeliveryResponse,
)
async def retry_webhook_delivery(
    endpoint_id: UUID,
    delivery_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    cipher: Annotated[SecretCipher, Depends(webhook_cipher)],
    sender: Annotated[WebhookSender, Depends(webhook_sender_from_request)],
) -> WebhookDeliveryResponse:
    try:
        WebhookService.require_admin(context)
        delivery = await WebhookDeliveryService(session, cipher, sender).deliver(
            context.organization_id,
            endpoint_id,
            delivery_id,
        )
    except WebhookAccessForbidden as exc:
        raise HTTPException(status_code=403, detail="Webhook administration is forbidden") from exc
    except WebhookEndpointNotFound as exc:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found") from exc
    except WebhookDeliveryNotFound as exc:
        raise HTTPException(status_code=404, detail="Webhook delivery not found") from exc
    return delivery_response(delivery)


def delivery_response(delivery: WebhookDelivery) -> WebhookDeliveryResponse:
    return WebhookDeliveryResponse(
        id=delivery.id,
        endpoint_id=delivery.endpoint_id,
        event_id=delivery.event_id,
        event_type=delivery.event_type,
        status=delivery.status,
        attempts=delivery.attempts,
        next_attempt_at=delivery.next_attempt_at,
        response_status=delivery.response_status,
        last_error=delivery.last_error,
        delivered_at=delivery.delivered_at,
        created_at=delivery.created_at,
        updated_at=delivery.updated_at,
    )
