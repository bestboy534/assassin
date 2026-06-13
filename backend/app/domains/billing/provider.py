import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.core.config import Settings


class InvalidBillingWebhook(Exception):
    pass


@dataclass(frozen=True)
class CustomerPayload:
    organization_id: UUID
    email: str
    idempotency_key: str


@dataclass(frozen=True)
class CheckoutPayload:
    customer_id: str
    plan_key: str
    success_url: str
    cancel_url: str
    idempotency_key: str


@dataclass(frozen=True)
class ExternalRef:
    external_id: str


@dataclass(frozen=True)
class BillingEvent:
    event_id: str
    event_type: str
    object_id: str
    version: int
    occurred_at: datetime
    data: dict[str, object]


class BillingProvider(Protocol):
    async def create_customer(self, payload: CustomerPayload) -> ExternalRef: ...

    async def create_checkout(self, payload: CheckoutPayload) -> str: ...

    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str: ...

    def verify_webhook(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> BillingEvent: ...


class FakeBillingProvider:
    def __init__(
        self,
        webhook_secret: str,
        timestamp_tolerance_seconds: int = 300,
    ) -> None:
        self.webhook_secret = webhook_secret.encode()
        self.timestamp_tolerance_seconds = timestamp_tolerance_seconds

    async def create_customer(self, payload: CustomerPayload) -> ExternalRef:
        digest = hashlib.sha256(payload.idempotency_key.encode()).hexdigest()[:20]
        return ExternalRef(external_id=f"cus_fake_{digest}")

    async def create_checkout(self, payload: CheckoutPayload) -> str:
        digest = hashlib.sha256(payload.idempotency_key.encode()).hexdigest()[:24]
        return f"https://billing.example.test/checkout/{digest}"

    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        digest = hashlib.sha256(
            f"{customer_id}:{return_url}".encode()
        ).hexdigest()[:24]
        return f"https://billing.example.test/portal/{digest}"

    def verify_webhook(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> BillingEvent:
        normalized = {key.lower(): value for key, value in headers.items()}
        timestamp_value = normalized.get("x-billing-timestamp", "")
        signature = normalized.get("x-billing-signature", "")
        try:
            timestamp = int(timestamp_value)
        except ValueError as exc:
            raise InvalidBillingWebhook from exc
        now = int(datetime.now(UTC).timestamp())
        if abs(now - timestamp) > self.timestamp_tolerance_seconds:
            raise InvalidBillingWebhook
        expected = hmac.new(
            self.webhook_secret,
            timestamp_value.encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise InvalidBillingWebhook

        try:
            payload = json.loads(body)
            event_id = str(payload["id"])
            event_type = str(payload["type"])
            object_id = str(payload["object_id"])
            version = int(payload["version"])
            occurred_at = datetime.fromisoformat(str(payload["created_at"]))
            data = payload["data"]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise InvalidBillingWebhook from exc
        if (
            not event_id
            or not event_type
            or not object_id
            or version < 0
            or not isinstance(data, dict)
        ):
            raise InvalidBillingWebhook
        return BillingEvent(
            event_id=event_id,
            event_type=event_type,
            object_id=object_id,
            version=version,
            occurred_at=self._as_utc(occurred_at),
            data=data,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def build_billing_provider(settings: Settings) -> BillingProvider:
    if settings.billing_provider == "fake":
        return FakeBillingProvider(
            settings.billing_webhook_secret.get_secret_value(),
            settings.billing_webhook_tolerance_seconds,
        )
    raise RuntimeError(f"Unsupported billing provider: {settings.billing_provider}")
