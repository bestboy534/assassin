import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from app.core.config import Settings


class InvalidPaymentWebhook(Exception):
    pass


@dataclass(frozen=True)
class PaymentLimits:
    single: Decimal
    daily: Decimal
    monthly: Decimal
    total: Decimal


@dataclass(frozen=True)
class CreateInstrument:
    idempotency_key: str
    owner_name: str
    merchant_lock: str
    currency: str
    limits: PaymentLimits


@dataclass(frozen=True)
class ProviderInstrument:
    external_id: str
    brand: str
    last4: str
    status: str
    sandbox: bool


@dataclass(frozen=True)
class ProviderEvent:
    event_id: str
    event_type: str
    external_id: str
    payload: dict[str, Any]


class PaymentProvider(Protocol):
    async def create_instrument(self, request: CreateInstrument) -> ProviderInstrument: ...

    async def update_limits(
        self,
        external_id: str,
        limits: PaymentLimits,
    ) -> ProviderInstrument: ...

    async def freeze(self, external_id: str) -> ProviderInstrument: ...

    async def unfreeze(self, external_id: str) -> ProviderInstrument: ...

    async def close(self, external_id: str) -> ProviderInstrument: ...

    def verify_webhook(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> ProviderEvent: ...


class FakePaymentProvider:
    def __init__(
        self,
        webhook_secret: str,
        timestamp_tolerance_seconds: int = 300,
    ) -> None:
        self.webhook_secret = webhook_secret.encode()
        self.timestamp_tolerance_seconds = timestamp_tolerance_seconds

    async def create_instrument(self, request: CreateInstrument) -> ProviderInstrument:
        digest = hashlib.sha256(request.idempotency_key.encode()).hexdigest()[:20]
        return ProviderInstrument(
            external_id=f"sandbox_{digest}",
            brand="Visa",
            last4="4242",
            status="active",
            sandbox=True,
        )

    async def update_limits(
        self,
        external_id: str,
        limits: PaymentLimits,
    ) -> ProviderInstrument:
        return self._instrument(external_id, "active")

    async def freeze(self, external_id: str) -> ProviderInstrument:
        return self._instrument(external_id, "pending")

    async def unfreeze(self, external_id: str) -> ProviderInstrument:
        return self._instrument(external_id, "pending")

    async def close(self, external_id: str) -> ProviderInstrument:
        return self._instrument(external_id, "pending")

    def verify_webhook(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> ProviderEvent:
        normalized = {key.lower(): value for key, value in headers.items()}
        timestamp_value = normalized.get("x-payment-timestamp", "")
        signature = normalized.get("x-payment-signature", "")
        try:
            timestamp = int(timestamp_value)
        except ValueError as exc:
            raise InvalidPaymentWebhook from exc
        now = int(datetime.now(UTC).timestamp())
        if abs(now - timestamp) > self.timestamp_tolerance_seconds:
            raise InvalidPaymentWebhook
        expected = hmac.new(
            self.webhook_secret,
            timestamp_value.encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise InvalidPaymentWebhook
        try:
            payload = json.loads(body)
            event_id = str(payload["event_id"])
            event_type = str(payload["type"])
            external_id = str(payload["external_id"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise InvalidPaymentWebhook from exc
        if not event_id or not event_type or not external_id:
            raise InvalidPaymentWebhook
        return ProviderEvent(
            event_id=event_id,
            event_type=event_type,
            external_id=external_id,
            payload=payload,
        )

    @staticmethod
    def _instrument(external_id: str, status: str) -> ProviderInstrument:
        return ProviderInstrument(
            external_id=external_id,
            brand="Visa",
            last4="4242",
            status=status,
            sandbox=True,
        )


def build_payment_provider(settings: Settings) -> PaymentProvider:
    if settings.payment_provider == "fake":
        return FakePaymentProvider(
            webhook_secret=settings.payment_webhook_secret.get_secret_value(),
            timestamp_tolerance_seconds=settings.payment_webhook_tolerance_seconds,
        )
    raise RuntimeError(f"Unsupported payment provider: {settings.payment_provider}")
