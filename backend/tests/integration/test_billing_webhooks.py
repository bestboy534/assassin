import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.billing.handler import BillingEventHandler
from app.domains.billing.models import (
    BillingCustomer,
    BillingInvoice,
    OrganizationSubscription,
)
from app.domains.billing.provider import (
    BillingEvent,
    CheckoutPayload,
    CustomerPayload,
    FakeBillingProvider,
    InvalidBillingWebhook,
)
from app.domains.identity.service import IdentityService
from app.domains.organizations.models import Organization
from app.main import app


async def _registered_organization(session: AsyncSession, email: str) -> Organization:
    user, _ = await IdentityService(session).register(
        email=email,
        password="Long passphrase 2026!",
        display_name="Billing Owner",
        organization_name=f"{email} Org",
        user_agent="pytest",
    )
    organization = await session.scalar(
        select(Organization).where(Organization.created_by_user_id == user.id)
    )
    assert organization is not None
    return organization


def _event(
    *,
    event_id: str,
    event_type: str,
    object_id: str,
    version: int,
    data: dict[str, object],
) -> BillingEvent:
    return BillingEvent(
        event_id=event_id,
        event_type=event_type,
        object_id=object_id,
        version=version,
        occurred_at=datetime(2026, 6, 13, 10, 0, tzinfo=UTC),
        data=data,
    )


async def test_out_of_order_webhook_does_not_revert_newer_subscription(
    database: Database,
) -> None:
    async with database.session_factory() as session:
        organization = await _registered_organization(
            session,
            "billing-order@example.com",
        )
        handler = BillingEventHandler(session, provider_name="fake")
        newer = _event(
            event_id="evt_subscription_20",
            event_type="subscription.updated",
            object_id="sub_ordered",
            version=20,
            data={
                "organization_id": str(organization.id),
                "plan_key": "starter",
                "status": "active",
                "current_period_start": "2026-06-01T00:00:00+00:00",
                "current_period_end": "2026-07-01T00:00:00+00:00",
            },
        )
        older = _event(
            event_id="evt_subscription_10",
            event_type="subscription.updated",
            object_id="sub_ordered",
            version=10,
            data={
                "organization_id": str(organization.id),
                "plan_key": "starter",
                "status": "cancelled",
            },
        )

        applied = await handler.handle(newer)
        stale = await handler.handle(older)
        duplicate = await handler.handle(newer)
        subscription = await session.scalar(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == organization.id
            )
        )

        assert applied.duplicate is False
        assert applied.stale is False
        assert stale.duplicate is False
        assert stale.stale is True
        assert duplicate.duplicate is True
        assert subscription is not None
        assert subscription.status == "active"
        assert subscription.provider_version == 20
        assert subscription.provider_subscription_id == "sub_ordered"


async def test_customer_invoice_payment_refund_and_dispute_events_are_synchronized(
    database: Database,
) -> None:
    async with database.session_factory() as session:
        organization = await _registered_organization(
            session,
            "billing-events@example.com",
        )
        handler = BillingEventHandler(session, provider_name="fake")
        await handler.handle(
            _event(
                event_id="evt_customer",
                event_type="customer.updated",
                object_id="cus_123",
                version=1,
                data={
                    "organization_id": str(organization.id),
                    "billing_email": "billing@example.com",
                    "status": "active",
                },
            )
        )
        await handler.handle(
            _event(
                event_id="evt_invoice",
                event_type="invoice.updated",
                object_id="inv_123",
                version=1,
                data={
                    "organization_id": str(organization.id),
                    "customer_id": "cus_123",
                    "status": "open",
                    "currency": "USD",
                    "amount_due_minor": 12000,
                    "amount_paid_minor": 0,
                    "hosted_invoice_url": "https://billing.example.test/invoices/inv_123",
                    "due_at": "2026-06-20T00:00:00+00:00",
                },
            )
        )
        await handler.handle(
            _event(
                event_id="evt_payment_failed",
                event_type="payment.failed",
                object_id="pay_1",
                version=2,
                data={
                    "organization_id": str(organization.id),
                    "subscription_id": "sub_events",
                    "invoice_id": "inv_123",
                },
            )
        )
        await handler.handle(
            _event(
                event_id="evt_payment_succeeded",
                event_type="payment.succeeded",
                object_id="pay_1",
                version=3,
                data={
                    "organization_id": str(organization.id),
                    "subscription_id": "sub_events",
                    "invoice_id": "inv_123",
                    "amount_paid_minor": 12000,
                    "paid_at": "2026-06-14T00:00:00+00:00",
                },
            )
        )
        await handler.handle(
            _event(
                event_id="evt_refund",
                event_type="refund.created",
                object_id="re_1",
                version=4,
                data={
                    "organization_id": str(organization.id),
                    "invoice_id": "inv_123",
                },
            )
        )
        await handler.handle(
            _event(
                event_id="evt_dispute",
                event_type="dispute.created",
                object_id="dp_1",
                version=5,
                data={
                    "organization_id": str(organization.id),
                    "invoice_id": "inv_123",
                },
            )
        )

        customer = await session.scalar(
            select(BillingCustomer).where(
                BillingCustomer.external_customer_id == "cus_123"
            )
        )
        invoice = await session.scalar(
            select(BillingInvoice).where(
                BillingInvoice.external_invoice_id == "inv_123"
            )
        )
        subscription = await session.scalar(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == organization.id
            )
        )

        assert customer is not None
        assert customer.billing_email == "billing@example.com"
        assert invoice is not None
        assert invoice.status == "disputed"
        assert invoice.amount_paid_minor == 12000
        assert invoice.paid_at is not None
        assert subscription is not None
        assert subscription.status == "active"
        assert subscription.provider_version == 3


async def test_fake_billing_provider_contract_and_signature() -> None:
    provider = FakeBillingProvider("billing-secret", timestamp_tolerance_seconds=300)
    customer = await provider.create_customer(
        CustomerPayload(
            organization_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="owner@example.com",
            idempotency_key="org-1",
        )
    )
    checkout_url = await provider.create_checkout(
        CheckoutPayload(
            customer_id=customer.external_id,
            plan_key="starter",
            success_url="https://app.example.test/success",
            cancel_url="https://app.example.test/cancel",
            idempotency_key="checkout-1",
        )
    )
    portal_url = await provider.create_portal_session(
        customer.external_id,
        "https://app.example.test/billing",
    )

    assert customer.external_id.startswith("cus_fake_")
    assert checkout_url.startswith("https://billing.example.test/checkout/")
    assert portal_url.startswith("https://billing.example.test/portal/")

    body = json.dumps(
        {
            "id": "evt_signed",
            "type": "subscription.updated",
            "object_id": "sub_signed",
            "version": 7,
            "created_at": "2026-06-13T10:00:00+00:00",
            "data": {"organization_id": "00000000-0000-0000-0000-000000000001"},
        },
        separators=(",", ":"),
    ).encode()
    timestamp = str(int(datetime.now(UTC).timestamp()))
    signature = hmac.new(
        b"billing-secret",
        timestamp.encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    event = provider.verify_webhook(
        {
            "X-Billing-Timestamp": timestamp,
            "X-Billing-Signature": signature,
        },
        body,
    )
    assert event.event_id == "evt_signed"
    assert event.version == 7

    try:
        provider.verify_webhook(
            {
                "X-Billing-Timestamp": timestamp,
                "X-Billing-Signature": "invalid",
            },
            body,
        )
    except InvalidBillingWebhook:
        pass
    else:
        raise AssertionError("Invalid billing signature should be rejected")


def test_billing_webhook_route_verifies_signature(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'billing-webhook.db'}",
        billing_provider="fake",
        billing_webhook_secret="billing-route-secret",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            registered = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "billing-route@example.com",
                    "password": "Long passphrase 2026!",
                    "display_name": "Billing Route",
                    "organization_name": "Billing Route Org",
                },
            )
            assert registered.status_code == 201
            organization_id = registered.json()["organizations"][0]["id"]
            body = json.dumps(
                {
                    "id": "evt_route",
                    "type": "subscription.updated",
                    "object_id": "sub_route",
                    "version": 9,
                    "created_at": "2026-06-13T10:00:00+00:00",
                    "data": {
                        "organization_id": organization_id,
                        "plan_key": "starter",
                        "status": "active",
                    },
                },
                separators=(",", ":"),
            ).encode()
            timestamp = str(int(datetime.now(UTC).timestamp()))
            signature = hmac.new(
                b"billing-route-secret",
                timestamp.encode() + b"." + body,
                hashlib.sha256,
            ).hexdigest()

            accepted = client.post(
                "/api/v1/billing/webhooks/fake",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Billing-Timestamp": timestamp,
                    "X-Billing-Signature": signature,
                },
            )
            rejected = client.post(
                "/api/v1/billing/webhooks/fake",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Billing-Timestamp": timestamp,
                    "X-Billing-Signature": "invalid",
                },
            )

            assert accepted.status_code == 200
            assert accepted.json() == {
                "accepted": True,
                "duplicate": False,
                "stale": False,
                "event_id": "evt_route",
            }
            assert rejected.status_code == 400
    finally:
        app.dependency_overrides.clear()
