import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

import httpx
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.infrastructure.secrets import SecretCipher

from .models import WebhookDelivery
from .service import (
    WebhookDeliveryNotFound,
    WebhookSecretUnavailable,
    WebhookService,
)


@dataclass(frozen=True)
class WebhookSendResult:
    status_code: int
    response_body: str


class WebhookSender(Protocol):
    async def send(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
    ) -> WebhookSendResult: ...


class HttpxWebhookSender:
    async def send(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
    ) -> WebhookSendResult:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, content=body)
        return WebhookSendResult(
            status_code=response.status_code,
            response_body=response.text[:500],
        )


class WebhookDeliveryService:
    def __init__(
        self,
        session: AsyncSession,
        cipher: SecretCipher,
        sender: WebhookSender,
    ) -> None:
        self.session = session
        self.webhooks = WebhookService(session, cipher)
        self.sender = sender

    async def deliver_due(
        self,
        *,
        now: datetime | None = None,
        limit: int = 100,
        max_attempts: int = 8,
    ) -> list[WebhookDelivery]:
        attempted_at = now or datetime.now(UTC)
        due = list(
            (
                await self.session.scalars(
                    select(WebhookDelivery)
                    .where(
                        WebhookDelivery.status == "pending",
                        WebhookDelivery.next_attempt_at <= attempted_at,
                    )
                    .order_by(
                        WebhookDelivery.next_attempt_at.asc(),
                        WebhookDelivery.created_at.asc(),
                    )
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        results: list[WebhookDelivery] = []
        for delivery in due:
            results.append(
                await self.deliver(
                    delivery.organization_id,
                    delivery.endpoint_id,
                    delivery.id,
                    now=attempted_at,
                    max_attempts=max_attempts,
                )
            )
        return results

    async def deliver(
        self,
        organization_id: UUID,
        endpoint_id: UUID,
        delivery_id: UUID,
        *,
        now: datetime | None = None,
        max_attempts: int = 8,
    ) -> WebhookDelivery:
        attempted_at = now or datetime.now(UTC)
        endpoint = await self.webhooks.get_endpoint(organization_id, endpoint_id)
        delivery = await self.session.scalar(
            select(WebhookDelivery).where(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.endpoint_id == endpoint_id,
                WebhookDelivery.organization_id == organization_id,
            )
        )
        if delivery is None:
            raise WebhookDeliveryNotFound(str(delivery_id))
        if delivery.status == "delivered":
            return delivery
        try:
            secret = self.webhooks.decrypt_secret(
                endpoint,
                delivery.secret_version,
                now=attempted_at,
            )
        except WebhookSecretUnavailable:
            async with transaction(self.session):
                delivery.status = "dead_letter"
                delivery.last_error = "Webhook signing secret is no longer available"
                delivery.next_attempt_at = attempted_at
            await self.session.commit()
            await self.session.refresh(delivery)
            return delivery

        body = self._body(delivery)
        timestamp = str(int(attempted_at.timestamp()))
        signature = hmac.new(
            secret.encode(),
            timestamp.encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Id": str(delivery.event_id),
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": f"v1={signature}",
        }
        try:
            result = await self.sender.send(endpoint.url, headers, body)
        except Exception as exc:
            return await self._record_failure(
                delivery,
                attempted_at=attempted_at,
                max_attempts=max_attempts,
                error=str(exc) or exc.__class__.__name__,
            )
        async with transaction(self.session):
            delivery.attempts += 1
            delivery.response_status = result.status_code
            delivery.response_body = result.response_body[:500]
            if 200 <= result.status_code < 300:
                delivery.status = "delivered"
                delivery.delivered_at = attempted_at
                delivery.last_error = None
                delivery.next_attempt_at = attempted_at
            else:
                delivery.last_error = f"HTTP {result.status_code}"
                delivery.status = (
                    "dead_letter"
                    if delivery.attempts >= max_attempts
                    else "pending"
                )
                delivery.next_attempt_at = attempted_at + self._retry_delay(
                    delivery.attempts
                )
        await self.session.commit()
        await self.session.refresh(delivery)
        return delivery

    async def _record_failure(
        self,
        delivery: WebhookDelivery,
        *,
        attempted_at: datetime,
        max_attempts: int,
        error: str,
    ) -> WebhookDelivery:
        async with transaction(self.session):
            delivery.attempts += 1
            delivery.last_error = error[:500]
            delivery.status = (
                "dead_letter" if delivery.attempts >= max_attempts else "pending"
            )
            delivery.next_attempt_at = attempted_at + self._retry_delay(delivery.attempts)
        await self.session.commit()
        await self.session.refresh(delivery)
        return delivery

    @staticmethod
    def _body(delivery: WebhookDelivery) -> bytes:
        payload = {
            "id": str(delivery.event_id),
            "type": delivery.event_type,
            "created_at": delivery.created_at,
            "data": delivery.payload_json,
        }
        return json.dumps(
            jsonable_encoder(payload),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

    @staticmethod
    def _retry_delay(attempts: int) -> timedelta:
        return timedelta(seconds=min(2**attempts, 3600))
