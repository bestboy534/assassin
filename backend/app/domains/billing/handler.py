from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.outbox.repository import record_inbox_receipt

from .models import (
    BillingCustomer,
    BillingInvoice,
    OrganizationSubscription,
    Plan,
)
from .provider import BillingEvent
from .subscriptions import READ_ONLY_STATUSES, SUBSCRIPTION_STATUSES

SUPPORTED_BILLING_EVENTS = {
    "customer.created",
    "customer.updated",
    "customer.deleted",
    "subscription.created",
    "subscription.updated",
    "subscription.deleted",
    "invoice.created",
    "invoice.updated",
    "invoice.paid",
    "invoice.payment_failed",
    "payment.succeeded",
    "payment.failed",
    "refund.created",
    "dispute.created",
}


class UnsupportedBillingEvent(Exception):
    pass


class BillingObjectNotFound(Exception):
    pass


class InvalidBillingEvent(Exception):
    pass


@dataclass(frozen=True)
class BillingHandleResult:
    event_id: str
    duplicate: bool
    stale: bool


class BillingEventHandler:
    def __init__(self, session: AsyncSession, provider_name: str) -> None:
        self.session = session
        self.provider_name = provider_name

    async def handle(self, event: BillingEvent) -> BillingHandleResult:
        if event.event_type not in SUPPORTED_BILLING_EVENTS:
            raise UnsupportedBillingEvent(event.event_type)
        receipt_id = uuid5(
            NAMESPACE_URL,
            f"billing:{self.provider_name}:{event.event_id}",
        )
        async with transaction(self.session):
            accepted = await record_inbox_receipt(
                self.session,
                f"billing:{self.provider_name}",
                receipt_id,
            )
            if not accepted:
                return BillingHandleResult(
                    event_id=event.event_id,
                    duplicate=True,
                    stale=False,
                )
            stale = await self._dispatch(event)
        return BillingHandleResult(
            event_id=event.event_id,
            duplicate=False,
            stale=stale,
        )

    async def _dispatch(self, event: BillingEvent) -> bool:
        if event.event_type.startswith("customer."):
            await self._sync_customer(event)
            return False
        if event.event_type.startswith("subscription."):
            return await self._sync_subscription(event)
        if event.event_type.startswith("invoice."):
            await self._sync_invoice(event)
            return False
        if event.event_type == "payment.failed":
            return await self._sync_payment(event, succeeded=False)
        if event.event_type == "payment.succeeded":
            return await self._sync_payment(event, succeeded=True)
        if event.event_type == "refund.created":
            await self._set_invoice_status(event, "refunded")
            return False
        if event.event_type == "dispute.created":
            await self._set_invoice_status(event, "disputed")
            return False
        raise UnsupportedBillingEvent(event.event_type)

    async def _sync_customer(self, event: BillingEvent) -> None:
        organization_id = self._organization_id(event)
        customer = await self.session.scalar(
            select(BillingCustomer).where(
                BillingCustomer.provider == self.provider_name,
                BillingCustomer.external_customer_id == event.object_id,
            )
        )
        if customer is None:
            customer = await self.session.scalar(
                select(BillingCustomer).where(
                    BillingCustomer.organization_id == organization_id
                )
            )
        if customer is None:
            customer = BillingCustomer(
                organization_id=organization_id,
                provider=self.provider_name,
                external_customer_id=event.object_id,
                status="active",
            )
            self.session.add(customer)
        customer.provider = self.provider_name
        customer.external_customer_id = event.object_id
        customer.billing_email = self._optional_str(
            event.data.get("billing_email")
        )
        customer.status = (
            "deleted"
            if event.event_type == "customer.deleted"
            else self._optional_str(event.data.get("status")) or "active"
        )
        await self.session.flush()

    async def _sync_subscription(self, event: BillingEvent) -> bool:
        organization_id = self._organization_id(event)
        subscription = await self._subscription(
            organization_id,
            self._optional_str(event.data.get("subscription_id"))
            or event.object_id,
        )
        if event.version <= subscription.provider_version:
            return True

        status = (
            "cancelled"
            if event.event_type == "subscription.deleted"
            else self._required_str(event.data, "status")
        )
        if status not in SUBSCRIPTION_STATUSES:
            raise InvalidBillingEvent(f"Unsupported subscription status: {status}")
        plan_key = self._optional_str(event.data.get("plan_key"))
        if plan_key is not None:
            plan = await self.session.scalar(select(Plan).where(Plan.key == plan_key))
            if plan is None:
                raise BillingObjectNotFound(f"Plan not found: {plan_key}")
            subscription.plan_id = plan.id

        subscription.provider = self.provider_name
        subscription.provider_subscription_id = event.object_id
        subscription.provider_version = event.version
        subscription.status = status
        subscription.read_only = status in READ_ONLY_STATUSES
        subscription.current_period_start = self._optional_datetime(
            event.data.get("current_period_start")
        )
        subscription.current_period_end = self._optional_datetime(
            event.data.get("current_period_end")
        )
        subscription.cancel_at_period_end = bool(
            event.data.get("cancel_at_period_end", status == "cancel_at_period_end")
        )
        subscription.cancelled_at = (
            self._optional_datetime(event.data.get("cancelled_at"))
            or (event.occurred_at if status == "cancelled" else None)
        )
        await self.session.flush()
        return False

    async def _sync_invoice(self, event: BillingEvent) -> None:
        organization_id = self._organization_id(event)
        external_customer_id = self._required_str(event.data, "customer_id")
        customer = await self.session.scalar(
            select(BillingCustomer).where(
                BillingCustomer.provider == self.provider_name,
                BillingCustomer.external_customer_id == external_customer_id,
            )
        )
        if customer is None:
            raise BillingObjectNotFound(
                f"Billing customer not found: {external_customer_id}"
            )
        invoice = await self.session.scalar(
            select(BillingInvoice).where(
                BillingInvoice.provider == self.provider_name,
                BillingInvoice.external_invoice_id == event.object_id,
            )
        )
        if invoice is None:
            invoice = BillingInvoice(
                organization_id=organization_id,
                billing_customer_id=customer.id,
                provider=self.provider_name,
                external_invoice_id=event.object_id,
                status="open",
                currency="USD",
            )
            self.session.add(invoice)
        invoice.billing_customer_id = customer.id
        invoice.status = self._invoice_status(event)
        invoice.currency = self._optional_str(event.data.get("currency")) or "USD"
        invoice.amount_due_minor = self._optional_int(
            event.data.get("amount_due_minor")
        )
        invoice.amount_paid_minor = self._optional_int(
            event.data.get("amount_paid_minor")
        )
        invoice.hosted_invoice_url = self._optional_str(
            event.data.get("hosted_invoice_url")
        )
        invoice.due_at = self._optional_datetime(event.data.get("due_at"))
        invoice.paid_at = self._optional_datetime(event.data.get("paid_at"))
        await self.session.flush()

    async def _sync_payment(
        self,
        event: BillingEvent,
        *,
        succeeded: bool,
    ) -> bool:
        organization_id = self._organization_id(event)
        subscription_id = self._required_str(event.data, "subscription_id")
        subscription = await self._subscription(organization_id, subscription_id)
        stale = event.version <= subscription.provider_version
        if not stale:
            subscription.provider = self.provider_name
            subscription.provider_subscription_id = subscription_id
            subscription.provider_version = event.version
            subscription.status = "active" if succeeded else "past_due"
            subscription.read_only = False

        invoice_id = self._optional_str(event.data.get("invoice_id"))
        if invoice_id is not None:
            invoice = await self._invoice(invoice_id)
            invoice.status = "paid" if succeeded else "past_due"
            if succeeded:
                invoice.amount_paid_minor = self._optional_int(
                    event.data.get("amount_paid_minor"),
                    fallback=invoice.amount_due_minor,
                )
                invoice.paid_at = (
                    self._optional_datetime(event.data.get("paid_at"))
                    or event.occurred_at
                )
        await self.session.flush()
        return stale

    async def _set_invoice_status(
        self,
        event: BillingEvent,
        status: str,
    ) -> None:
        invoice_id = self._required_str(event.data, "invoice_id")
        invoice = await self._invoice(invoice_id)
        invoice.status = status
        await self.session.flush()

    async def _subscription(
        self,
        organization_id: UUID,
        external_subscription_id: str,
    ) -> OrganizationSubscription:
        subscription = await self.session.scalar(
            select(OrganizationSubscription).where(
                OrganizationSubscription.provider == self.provider_name,
                OrganizationSubscription.provider_subscription_id
                == external_subscription_id,
            )
        )
        if subscription is None:
            subscription = await self.session.scalar(
                select(OrganizationSubscription).where(
                    OrganizationSubscription.organization_id == organization_id
                )
            )
        if subscription is None:
            raise BillingObjectNotFound(
                f"Subscription not found for organization {organization_id}"
            )
        return subscription

    async def _invoice(self, external_invoice_id: str) -> BillingInvoice:
        invoice = await self.session.scalar(
            select(BillingInvoice).where(
                BillingInvoice.provider == self.provider_name,
                BillingInvoice.external_invoice_id == external_invoice_id,
            )
        )
        if invoice is None:
            raise BillingObjectNotFound(
                f"Billing invoice not found: {external_invoice_id}"
            )
        return invoice

    @staticmethod
    def _organization_id(event: BillingEvent) -> UUID:
        try:
            return UUID(str(event.data["organization_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidBillingEvent("organization_id is required") from exc

    @staticmethod
    def _required_str(data: dict[str, object], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise InvalidBillingEvent(f"{key} is required")
        return value.strip()

    @staticmethod
    def _optional_str(value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise InvalidBillingEvent("Expected string value")
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _optional_int(value: object, *, fallback: int = 0) -> int:
        if value is None:
            return fallback
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise InvalidBillingEvent("Expected non-negative integer")
        return value

    @staticmethod
    def _optional_datetime(value: object) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise InvalidBillingEvent("Expected ISO datetime string")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise InvalidBillingEvent("Expected ISO datetime string") from exc
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _invoice_status(event: BillingEvent) -> str:
        if event.event_type == "invoice.paid":
            return "paid"
        if event.event_type == "invoice.payment_failed":
            return "past_due"
        return BillingEventHandler._required_str(event.data, "status")
