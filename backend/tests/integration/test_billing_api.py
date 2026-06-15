import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.billing.models import BillingCustomer, BillingInvoice
from app.domains.identity.models import User
from app.domains.organizations.models import OrganizationMember
from app.main import app


def _client(database: Database, tmp_path: Path) -> TestClient:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'billing-api.db'}",
        billing_provider="fake",
        billing_webhook_secret="billing-api-secret",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _register(
    client: TestClient,
    *,
    email: str,
    organization_name: str,
) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "Billing Owner",
            "organization_name": organization_name,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


def test_billing_owner_can_manage_subscription_usage_invoices_and_portal(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            organization_id, _ = _register(
                client,
                email="billing-api-owner@example.com",
                organization_name="Billing API Org",
            )

            plans = client.get("/api/v1/billing/plans")
            assert plans.status_code == 200
            assert [item["key"] for item in plans.json()["items"]] == [
                "starter",
                "pro",
            ]

            summary = client.get(
                f"/api/v1/organizations/{organization_id}/billing"
            )
            assert summary.status_code == 200
            assert summary.json()["plan"]["key"] == "starter"
            assert summary.json()["subscription"]["status"] == "trialing"

            preview = client.post(
                f"/api/v1/organizations/{organization_id}/billing/change-preview",
                json={"target_plan": "pro"},
            )
            assert preview.status_code == 200
            assert preview.json()["direction"] == "upgrade"
            assert preview.json()["target_amount_minor"] == 4900

            changed = client.post(
                f"/api/v1/organizations/{organization_id}/billing/change-plan",
                json={"target_plan": "pro"},
            )
            assert changed.status_code == 200
            assert changed.json()["plan"]["key"] == "pro"

            usage = client.get(
                f"/api/v1/organizations/{organization_id}/billing/usage"
            )
            assert usage.status_code == 200
            assert len(usage.json()["items"]) == 7

            async def add_invoice() -> None:
                async with database.session_factory() as session:
                    customer = BillingCustomer(
                        organization_id=UUID(organization_id),
                        provider="fake",
                        external_customer_id="cus_billing_api",
                        billing_email="billing@example.com",
                        status="active",
                    )
                    session.add(customer)
                    await session.flush()
                    session.add(
                        BillingInvoice(
                            organization_id=UUID(organization_id),
                            billing_customer_id=customer.id,
                            provider="fake",
                            external_invoice_id="inv_billing_api",
                            status="open",
                            currency="USD",
                            amount_due_minor=4900,
                            amount_paid_minor=0,
                            hosted_invoice_url=(
                                "https://billing.example.test/invoices/inv_billing_api"
                            ),
                            due_at=datetime(2026, 7, 1, tzinfo=UTC),
                        )
                    )
                    await session.commit()

            asyncio.run(add_invoice())
            invoices = client.get(
                f"/api/v1/organizations/{organization_id}/billing/invoices"
            )
            assert invoices.status_code == 200
            assert invoices.json()["items"][0]["external_invoice_id"] == (
                "inv_billing_api"
            )

            portal = client.post(
                f"/api/v1/organizations/{organization_id}/billing/portal-session",
                json={"return_url": "http://localhost:5173/app/acme/settings/billing"},
            )
            assert portal.status_code == 200
            assert portal.json()["url"].startswith(
                "https://billing.example.test/portal/"
            )

            cancelled = client.post(
                f"/api/v1/organizations/{organization_id}/billing/cancel"
            )
            assert cancelled.status_code == 200
            assert cancelled.json()["subscription"]["cancel_at_period_end"] is True
            restored = client.post(
                f"/api/v1/organizations/{organization_id}/billing/undo-cancellation"
            )
            assert restored.status_code == 200
            assert restored.json()["subscription"]["cancel_at_period_end"] is False
    finally:
        app.dependency_overrides.clear()


def test_billing_pages_are_forbidden_to_regular_members(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            owner_organization_id, _ = _register(
                client,
                email="billing-owner-role@example.com",
                organization_name="Owner Billing Org",
            )
            client.post("/api/v1/auth/logout")
            _, member_user_id = _register(
                client,
                email="billing-member-role@example.com",
                organization_name="Member Billing Org",
            )

            async def add_member() -> None:
                async with database.session_factory() as session:
                    member = await session.get(User, UUID(member_user_id))
                    assert member is not None
                    session.add(
                        OrganizationMember(
                            organization_id=UUID(owner_organization_id),
                            user_id=member.id,
                            role="member",
                            status="active",
                        )
                    )
                    await session.commit()

            asyncio.run(add_member())

            response = client.get(
                f"/api/v1/organizations/{owner_organization_id}/billing"
            )
            assert response.status_code == 403
            assert response.json()["detail"] == "Billing administration is forbidden"
    finally:
        app.dependency_overrides.clear()
