import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, update
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.compliance.models import AuditLog
from app.domains.compliance.service import AuditLogCreate, ComplianceService
from app.domains.organizations.models import OrganizationMember
from app.main import app


def _register(client: TestClient, email: str, organization: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "安全负责人",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


def test_audit_log_cannot_be_updated_or_deleted(database: Database) -> None:
    async def run() -> None:
        organization_id = UUID("00000000-0000-0000-0000-000000000001")
        actor_id = UUID("00000000-0000-0000-0000-000000000002")
        async with database.session_factory() as session:
            created = await ComplianceService(session).record_audit_log(
                AuditLogCreate(
                    organization_id=organization_id,
                    actor_type="user",
                    actor_id=actor_id,
                    action="api_key.created",
                    resource_type="api_key",
                    resource_id="key_123",
                    metadata={"safe": "kept"},
                )
            )
            created_id = created.id

            with pytest.raises(DatabaseError):
                await session.execute(
                    update(AuditLog)
                    .where(AuditLog.id == created_id)
                    .values(action="changed")
                )
                await session.commit()
            await session.rollback()

            with pytest.raises(DatabaseError):
                await session.execute(delete(AuditLog).where(AuditLog.id == created_id))
                await session.commit()
            await session.rollback()

            current = await session.get(AuditLog, created_id)
            assert current is not None
            assert current.action == "api_key.created"

    asyncio.run(run())


def test_audit_log_api_lists_details_exports_and_redacts_sensitive_values(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'compliance.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id, user_id = _register(client, "security@example.com", "安全组织")

            async def seed_log() -> str:
                async with database.session_factory() as session:
                    created = await ComplianceService(session).record_audit_log(
                        AuditLogCreate(
                            organization_id=UUID(org_id),
                            actor_type="user",
                            actor_id=UUID(user_id),
                            action="api_key.created",
                            resource_type="api_key",
                            resource_id="key_123",
                            ip_address="127.0.0.1",
                            user_agent="pytest client",
                            request_id="req-123",
                            before={},
                            after={"name": "BI export", "token": "secret-token"},
                            metadata={
                                "safe": "kept",
                                "password": "super-secret",
                                "nested": {"cookie": "session-cookie"},
                            },
                        )
                    )
                    return str(created.id)

            audit_id = asyncio.run(seed_log())

            listed = client.get(f"/api/v1/organizations/{org_id}/audit-logs")
            assert listed.status_code == 200
            assert "super-secret" not in listed.text
            assert "secret-token" not in listed.text
            assert "session-cookie" not in listed.text
            payload = listed.json()
            assert payload["items"][0]["action"] == "api_key.created"
            assert payload["items"][0]["metadata"]["safe"] == "kept"
            assert payload["items"][0]["metadata"]["password"] == "[REDACTED]"

            detail = client.get(f"/api/v1/organizations/{org_id}/audit-logs/{audit_id}")
            assert detail.status_code == 200
            assert detail.json()["id"] == audit_id

            client.post("/api/v1/auth/logout")
            _, member_user_id = _register(client, "member-security@example.com", "成员组织")

            async def add_member_to_security_organization() -> None:
                async with database.session_factory() as session:
                    session.add(
                        OrganizationMember(
                            organization_id=UUID(org_id),
                            user_id=UUID(member_user_id),
                            role="member",
                            status="active",
                        )
                    )
                    await session.commit()

            asyncio.run(add_member_to_security_organization())
            forbidden = client.get(f"/api/v1/organizations/{org_id}/audit-logs")
            assert forbidden.status_code == 403

            client.post("/api/v1/auth/logout")
            logged_in = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "security@example.com",
                    "password": "Long passphrase 2026!",
                },
            )
            assert logged_in.status_code == 200

            exported = client.post(
                f"/api/v1/organizations/{org_id}/audit-logs/export",
                json={"format": "json"},
            )
            assert exported.status_code == 201
            assert exported.json()["format"] == "json"
            assert "super-secret" not in exported.text
            assert exported.json()["rows"][0]["action"] == "api_key.created"

            relisted = client.get(f"/api/v1/organizations/{org_id}/audit-logs")
            assert relisted.status_code == 200
            assert any(
                item["action"] == "audit_logs.exported"
                for item in relisted.json()["items"]
            )
    finally:
        app.dependency_overrides.clear()
