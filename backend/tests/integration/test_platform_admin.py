import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli import assign_platform_role
from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.admin.models import FeatureFlag, PlatformAuditLog
from app.domains.billing.models import OrganizationSubscription, Plan
from app.domains.identity.models import User
from app.domains.jobs.models import Job
from app.domains.organizations.models import Organization
from app.main import app


def _client(database: Database, tmp_path: Path) -> TestClient:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'admin.db'}",
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
            "display_name": "平台用户",
            "organization_name": organization_name,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Long passphrase 2026!"},
    )
    assert response.status_code == 200


async def _promote(database: Database, email: str, role: str) -> None:
    async with database.session_factory() as session:
        user = await session.scalar(
            select(User).where(User.email_normalized == email)
        )
        assert user is not None
        user.platform_role = role
        await session.commit()


def test_organization_admin_cannot_access_platform_admin(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            _register(
                client,
                email="organization-admin@example.com",
                organization_name="Customer Admin Org",
            )
            response = client.get("/api/v1/admin/organizations")
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_platform_role_is_bootstrapped_by_explicit_cli_action(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            _register(
                client,
                email="bootstrap-admin@example.com",
                organization_name="Bootstrap Org",
            )

        assert (
            asyncio.run(
                assign_platform_role(
                    "bootstrap-admin@example.com",
                    "platform_admin",
                    database,
                    reason="Initial production administrator bootstrap",
                )
            )
            == "platform_admin"
        )

        async def stored_role() -> str | None:
            async with database.session_factory() as session:
                user = await session.scalar(
                    select(User).where(
                        User.email_normalized == "bootstrap-admin@example.com"
                    )
                )
                assert user is not None
                return user.platform_role

        assert asyncio.run(stored_role()) == "platform_admin"
    finally:
        app.dependency_overrides.clear()


def test_platform_admin_can_read_controlled_operational_views(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            _register(
                client,
                email="platform-reader@example.com",
                organization_name="Platform Operations",
            )
            asyncio.run(
                _promote(database, "platform-reader@example.com", "platform_admin")
            )
            client.post("/api/v1/auth/logout")
            _login(client, "platform-reader@example.com")

            for path in (
                "/api/v1/admin/organizations",
                "/api/v1/admin/users",
                "/api/v1/admin/subscriptions",
                "/api/v1/admin/feature-flags",
                "/api/v1/admin/jobs",
                "/api/v1/admin/integrations",
                "/api/v1/admin/webhooks",
                "/api/v1/admin/email-deliveries",
                "/api/v1/admin/software-directory",
                "/api/v1/admin/cancellation-routes",
            ):
                response = client.get(path)
                assert response.status_code == 200, path
                assert "items" in response.json()

            openapi = client.get("/openapi.json").json()
            assert all("sql" not in path.casefold() for path in openapi["paths"])
    finally:
        app.dependency_overrides.clear()


def test_high_risk_admin_actions_require_reauth_reason_and_are_audited(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            admin_org_id, admin_user_id = _register(
                client,
                email="platform-operator@example.com",
                organization_name="Platform Operator Org",
            )
            asyncio.run(
                _promote(database, "platform-operator@example.com", "platform_admin")
            )
            client.post("/api/v1/auth/logout")
            target_org_id, target_user_id = _register(
                client,
                email="target-user@example.com",
                organization_name="Target Customer",
            )

            async def seed() -> tuple[UUID, UUID, UUID]:
                async with database.session_factory() as session:
                    failed_job = Job(
                        organization_id=UUID(target_org_id),
                        job_type="integration.sync",
                        status="failed",
                        payload_json={"connection_id": "connection-1"},
                        attempts=1,
                        max_attempts=3,
                        retryable=True,
                    )
                    feature_flag = FeatureFlag(
                        key="admin-console-preview",
                        description="Platform admin preview",
                        status="disabled",
                        rollout_percentage=0,
                    )
                    session.add_all([failed_job, feature_flag])
                    await session.flush()
                    subscription = await session.scalar(
                        select(OrganizationSubscription).where(
                            OrganizationSubscription.organization_id
                            == UUID(target_org_id)
                        )
                    )
                    assert subscription is not None
                    await session.commit()
                    return failed_job.id, feature_flag.id, subscription.id

            job_id, flag_id, subscription_id = asyncio.run(seed())
            client.post("/api/v1/auth/logout")
            _login(client, "platform-operator@example.com")

            rejected = client.post(
                f"/api/v1/admin/organizations/{target_org_id}/suspend",
                json={
                    "reason": "Security investigation pending review",
                    "reauth_confirmed": False,
                    "reauth_password": "Long passphrase 2026!",
                },
            )
            assert rejected.status_code == 428

            wrong_password = client.post(
                f"/api/v1/admin/organizations/{target_org_id}/suspend",
                json={
                    "reason": "Security investigation pending review",
                    "reauth_confirmed": True,
                    "reauth_password": "Incorrect passphrase 2026!",
                },
            )
            assert wrong_password.status_code == 428

            action = {
                "reason": "Security investigation approved by on-call lead",
                "reauth_confirmed": True,
                "reauth_password": "Long passphrase 2026!",
            }
            suspended = client.post(
                f"/api/v1/admin/organizations/{target_org_id}/suspend",
                json=action,
            )
            assert suspended.status_code == 200
            assert suspended.json()["status"] == "suspended"

            banned = client.post(
                f"/api/v1/admin/users/{target_user_id}/ban",
                json=action,
            )
            assert banned.status_code == 200
            assert banned.json()["status"] == "suspended"

            replayed = client.post(
                f"/api/v1/admin/jobs/{job_id}/replay",
                json=action,
            )
            assert replayed.status_code == 201
            assert replayed.json()["status"] == "queued"
            assert replayed.json()["id"] != str(job_id)

            changed = client.post(
                f"/api/v1/admin/subscriptions/{subscription_id}/change-plan",
                json={
                    **action,
                    "target_plan": "pro",
                },
            )
            assert changed.status_code == 200
            assert changed.json()["plan_key"] == "pro"

            enabled = client.post(
                f"/api/v1/admin/feature-flags/{flag_id}/enable",
                json={**action, "rollout_percentage": 25},
            )
            assert enabled.status_code == 200
            assert enabled.json()["status"] == "active"
            assert enabled.json()["rollout_percentage"] == 25

            async def verify_state() -> tuple[str, str, int]:
                async with database.session_factory() as session:
                    organization = await session.get(
                        Organization,
                        UUID(target_org_id),
                    )
                    user = await session.get(User, UUID(target_user_id))
                    audit_count = int(
                        await session.scalar(
                            select(func.count(PlatformAuditLog.id)).where(
                                PlatformAuditLog.actor_user_id
                                == UUID(admin_user_id)
                            )
                        )
                        or 0
                    )
                    assert organization is not None
                    assert user is not None
                    return organization.status, user.status, audit_count

            organization_status, user_status, audit_count = asyncio.run(verify_state())
            assert organization_status == "suspended"
            assert user_status == "suspended"
            assert audit_count == 5

            async def plan_key() -> str:
                async with database.session_factory() as session:
                    subscription = await session.get(
                        OrganizationSubscription,
                        subscription_id,
                    )
                    assert subscription is not None
                    plan = await session.get(Plan, subscription.plan_id)
                    assert plan is not None
                    return plan.key

            assert asyncio.run(plan_key()) == "pro"
            assert admin_org_id != target_org_id

            async def tamper_with_audit_log() -> None:
                async with database.session_factory() as session:
                    audit_log = await session.scalar(
                        select(PlatformAuditLog).order_by(
                            PlatformAuditLog.created_at
                        )
                    )
                    assert audit_log is not None
                    audit_log.reason = "Tampered reason"
                    with pytest.raises(DBAPIError):
                        await session.commit()
                    await session.rollback()

            asyncio.run(tamper_with_audit_log())
    finally:
        app.dependency_overrides.clear()
