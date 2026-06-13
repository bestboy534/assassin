from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.applications.models import Application
from app.domains.billing.models import UsageCounter, UsageEvent
from app.domains.billing.service import (
    EntitlementDenied,
    EntitlementService,
)
from app.main import app


def _register(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "billing-owner@example.com",
            "password": "Long passphrase 2026!",
            "display_name": "计费负责人",
            "organization_name": "Billing Org",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["user"]["id"], payload["organizations"][0]["id"]


def test_starter_application_limit_is_enforced_by_application_service(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'entitlements.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            _, organization_id = _register(client)

            for index in range(5):
                created = client.post(
                    f"/api/v1/organizations/{organization_id}/applications",
                    json={
                        "name": f"Application {index + 1}",
                        "category": "productivity",
                    },
                )
                assert created.status_code == 201

            blocked = client.post(
                f"/api/v1/organizations/{organization_id}/applications",
                json={"name": "One more", "category": "productivity"},
            )

            assert blocked.status_code == 403
            assert blocked.json()["detail"] == {
                "code": "entitlement_exceeded",
                "entitlement": "applications",
                "current": 5,
                "limit": 5,
                "increment": 1,
                "plan": "starter",
            }

            async def count_applications() -> int:
                async with database.session_factory() as session:
                    return int(
                        await session.scalar(
                            select(func.count(Application.id)).where(
                                Application.organization_id == UUID(organization_id),
                            )
                        )
                        or 0
                    )

            import asyncio

            assert asyncio.run(count_applications()) == 5
    finally:
        app.dependency_overrides.clear()


async def test_feature_overrides_and_usage_events_are_idempotent(
    database: Database,
) -> None:
    async with database.session_factory() as session:
        from app.domains.identity.models import User
        from app.domains.organizations.models import Organization
        from app.domains.organizations.service import OrganizationContext

        user = User(
            email_normalized="entitlement-service@example.com",
            password_hash="test",
            display_name="Entitlement Owner",
            status="active",
            email_verified_at=User.verified_now(),
        )
        session.add(user)
        await session.flush()
        organization = Organization(
            name="Entitlement Service Org",
            slug="entitlement-service-org",
            status="active",
            created_by_user_id=user.id,
        )
        session.add(organization)
        await session.flush()
        context = OrganizationContext(
            organization_id=organization.id,
            user_id=user.id,
            membership_id=user.id,
            role="owner",
        )
        service = EntitlementService(session)

        await service.ensure_default_subscription(context.organization_id)

        try:
            await service.require_feature(context, "api_access")
        except EntitlementDenied as exc:
            assert exc.entitlement == "api_access"
            assert exc.plan == "starter"
        else:
            raise AssertionError("Starter API access should be disabled")

        await service.set_organization_entitlement(
            context.organization_id,
            key="api_access",
            value_type="boolean",
            value=True,
            reason="Pilot override",
        )
        await service.require_feature(context, "api_access")

        first = await service.record_usage(
            context,
            metric="ai_pages",
            amount=3,
            source_key="analysis-run-1",
        )
        second = await service.record_usage(
            context,
            metric="ai_pages",
            amount=3,
            source_key="analysis-run-1",
        )

        assert first.current_value == 3
        assert second.current_value == 3
        assert (
            await session.scalar(
                select(func.count(UsageEvent.id)).where(
                    UsageEvent.organization_id == organization.id,
                    UsageEvent.metric == "ai_pages",
                )
            )
            == 1
        )
        counter = await session.scalar(
            select(UsageCounter).where(
                UsageCounter.organization_id == organization.id,
                UsageCounter.metric == "ai_pages",
            )
        )
        assert counter is not None
        assert counter.current_value == 3
