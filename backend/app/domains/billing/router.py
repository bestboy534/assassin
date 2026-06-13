from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import get_session

from .handler import (
    BillingEventHandler,
    BillingObjectNotFound,
    InvalidBillingEvent,
    UnsupportedBillingEvent,
)
from .provider import InvalidBillingWebhook, build_billing_provider
from .schemas import BillingWebhookResponse

webhook_router = APIRouter(
    prefix="/billing/webhooks",
    tags=["billing-webhooks"],
)


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
