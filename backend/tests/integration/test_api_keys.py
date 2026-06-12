import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.api_keys.models import ApiKey
from app.main import app


def _client(database: Database, tmp_path: Path) -> TestClient:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'api-keys.db'}",
        webhook_secret_key="test-webhook-secret",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _register(
    client: TestClient,
    email: str = "api-key-owner@example.com",
    organization: str = "API 密钥组织",
) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "密钥管理员",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


def test_api_key_secret_is_one_time_scoped_and_revocable(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            organization_id, _ = _register(client)
            created = client.post(
                f"/api/v1/organizations/{organization_id}/api-keys",
                json={
                    "name": "BI export",
                    "scopes": ["reports.read", "reports.export"],
                    "expires_at": (
                        datetime.now(UTC) + timedelta(days=30)
                    ).isoformat(),
                },
            )
            assert created.status_code == 201
            secret = created.json()["secret"]
            api_key_id = created.json()["id"]
            assert secret.startswith("ssa_")
            assert created.json()["prefix"] in secret

            listed = client.get(
                f"/api/v1/organizations/{organization_id}/api-keys"
            )
            assert listed.status_code == 200
            assert secret not in listed.text
            assert "secret_hash" not in listed.text
            assert listed.json()["items"][0]["scopes"] == [
                "reports.export",
                "reports.read",
            ]

            verified = client.get(
                "/api/v1/api-keys/current",
                params={"required_scope": "reports.read"},
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert verified.status_code == 200
            assert verified.json()["organization_id"] == organization_id
            assert verified.json()["api_key_id"] == api_key_id

            forbidden = client.get(
                "/api/v1/api-keys/current",
                params={"required_scope": "payments.write"},
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert forbidden.status_code == 403

            revoked = client.post(
                f"/api/v1/organizations/{organization_id}/api-keys/"
                f"{api_key_id}/revoke"
            )
            assert revoked.status_code == 200
            assert revoked.json()["revoked_at"] is not None

            rejected = client.get(
                "/api/v1/api-keys/current",
                headers={"Authorization": f"Bearer {secret}"},
            )
            assert rejected.status_code == 401

            async def inspect_record() -> tuple[str, datetime | None]:
                async with database.session_factory() as session:
                    record = await session.scalar(
                        select(ApiKey).where(ApiKey.id == UUID(api_key_id))
                    )
                    assert record is not None
                    assert secret not in record.secret_hash
                    return record.secret_hash, record.last_used_at

            secret_hash, last_used_at = asyncio.run(inspect_record())
            assert len(secret_hash) == 64
            assert last_used_at is not None
    finally:
        app.dependency_overrides.clear()
