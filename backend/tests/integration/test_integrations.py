import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.integrations.models import (
    IntegrationCredential,
    IntegrationOAuthState,
    SyncCursor,
)
from app.main import app


def _register(client: TestClient, email: str, organization: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "集成管理员",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    return response.json()["organizations"][0]["id"]


def test_integration_credentials_sync_cursor_errors_and_tenant_isolation(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'integrations.db'}",
        integration_secret_key="test-integration-secret",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id = _register(client, "integrations@example.com", "集成验证")
            definitions = client.get(
                f"/api/v1/organizations/{org_id}/integrations/definitions"
            )
            assert definitions.status_code == 200
            assert definitions.json()["items"][0]["key"] == "fake_identity"

            created = client.post(
                f"/api/v1/organizations/{org_id}/integrations/connections",
                json={
                    "definition_key": "fake_identity",
                    "display_name": "企业身份目录",
                    "api_token": "sandbox-token-1234",
                    "sandbox_options": {},
                },
            )
            assert created.status_code == 201
            connection = created.json()
            connection_id = connection["id"]
            assert connection["status"] == "connected"
            assert connection["credential_last4"] == "1234"
            assert "sandbox-token-1234" not in created.text
            assert "api_token" not in created.text

            listed = client.get(
                f"/api/v1/organizations/{org_id}/integrations/connections"
            )
            assert listed.status_code == 200
            assert "sandbox-token-1234" not in listed.text

            reconnected = client.post(
                f"/api/v1/organizations/{org_id}/integrations/connections/"
                f"{connection_id}/reconnect",
                json={"api_token": "sandbox-rotated-0000"},
            )
            assert reconnected.status_code == 200
            assert reconnected.json()["credential_last4"] == "0000"
            assert "sandbox-rotated-0000" not in reconnected.text

            tested = client.post(
                f"/api/v1/organizations/{org_id}/integrations/connections/"
                f"{connection_id}/test"
            )
            assert tested.status_code == 200
            assert tested.json()["healthy"] is True

            first_sync = client.post(
                f"/api/v1/organizations/{org_id}/integrations/connections/"
                f"{connection_id}/sync"
            )
            assert first_sync.status_code == 200
            run = first_sync.json()
            assert run["status"] == "succeeded"
            assert run["cursor_before"] is None
            assert run["cursor_after"] == "page-2"
            assert run["read_count"] == 2
            assert run["created_count"] == 2
            assert run["failed_count"] == 0

            applications = client.get(f"/api/v1/organizations/{org_id}/applications")
            assert {item["name"] for item in applications.json()["items"]} == {
                "Figma",
                "Notion",
            }

            second_sync = client.post(
                f"/api/v1/organizations/{org_id}/integrations/connections/"
                f"{connection_id}/sync"
            )
            assert second_sync.status_code == 200
            assert second_sync.json()["read_count"] == 0
            assert second_sync.json()["cursor_before"] == "page-2"
            assert second_sync.json()["cursor_after"] == "page-2"

            failing = client.post(
                f"/api/v1/organizations/{org_id}/integrations/connections",
                json={
                    "definition_key": "fake_identity",
                    "display_name": "失败诊断连接",
                    "api_token": "sandbox-failure-9876",
                    "sandbox_options": {"fail_on_page": 2},
                },
            ).json()
            failed_sync = client.post(
                f"/api/v1/organizations/{org_id}/integrations/connections/"
                f"{failing['id']}/sync"
            )
            assert failed_sync.status_code == 200
            assert failed_sync.json()["status"] == "failed"
            assert failed_sync.json()["cursor_after"] is None
            assert failed_sync.json()["read_count"] == 1
            assert failed_sync.json()["failed_count"] == 1

            runs = client.get(
                f"/api/v1/organizations/{org_id}/integrations/connections/"
                f"{failing['id']}/sync-runs"
            )
            assert runs.status_code == 200
            assert runs.json()["items"][0]["errors"][0]["code"] == "provider_error"

            paused = client.post(
                f"/api/v1/organizations/{org_id}/integrations/connections/"
                f"{connection_id}/pause"
            )
            assert paused.status_code == 200
            assert paused.json()["status"] == "paused"
            assert (
                client.post(
                    f"/api/v1/organizations/{org_id}/integrations/connections/"
                    f"{connection_id}/sync"
                ).status_code
                == 409
            )
            resumed = client.post(
                f"/api/v1/organizations/{org_id}/integrations/connections/"
                f"{connection_id}/resume"
            )
            assert resumed.status_code == 200
            assert resumed.json()["status"] == "connected"

            deleted = client.delete(
                f"/api/v1/organizations/{org_id}/integrations/connections/"
                f"{connection_id}"
            )
            assert deleted.status_code == 200
            assert deleted.json()["status"] == "deleted"
            assert deleted.json()["data_retention"] == "retain_synced_data"

            other_org = _register(client, "other-integrations@example.com", "其他组织")
            assert (
                client.get(
                    f"/api/v1/organizations/{other_org}/integrations/connections/"
                    f"{connection_id}"
                ).status_code
                == 404
            )

            async def inspect_secret_and_cursors() -> tuple[str, list[str]]:
                async with database.session_factory() as session:
                    credential = await session.scalar(
                        select(IntegrationCredential).where(
                            IntegrationCredential.connection_id == UUID(failing["id"])
                        )
                    )
                    cursors = (
                        await session.scalars(
                            select(SyncCursor).where(
                                SyncCursor.connection_id == UUID(failing["id"])
                            )
                        )
                    ).all()
                    assert credential is not None
                    return credential.ciphertext, [item.cursor for item in cursors]

            ciphertext, cursors = asyncio.run(inspect_secret_and_cursors())
            assert "sandbox-failure-9876" not in ciphertext
            assert cursors == []
    finally:
        app.dependency_overrides.clear()


def test_oauth_state_pkce_expiry_and_replay(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'oauth.db'}",
        integration_secret_key="test-integration-secret",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id = _register(client, "oauth-integrations@example.com", "OAuth 验证")
            started = client.post(
                f"/api/v1/organizations/{org_id}/integrations/oauth/"
                "fake_identity/start",
                json={
                    "redirect_uri": "https://app.example.com/integrations/oauth/callback"
                },
            )
            assert started.status_code == 201
            payload = started.json()
            state = payload["state"]
            assert state
            assert "code_challenge_method=S256" in payload["authorization_url"]
            assert "pkce_verifier" not in started.text

            async def inspect_oauth_state() -> tuple[str, str]:
                async with database.session_factory() as session:
                    oauth_state = await session.scalar(select(IntegrationOAuthState))
                    assert oauth_state is not None
                    return oauth_state.state_hash, oauth_state.pkce_verifier_hash

            state_hash, verifier_hash = asyncio.run(inspect_oauth_state())
            assert state not in state_hash
            assert len(state_hash) == 64
            assert len(verifier_hash) == 64

            callback = client.get(
                f"/api/v1/organizations/{org_id}/integrations/oauth/callback",
                params={"state": state, "code": "sandbox-code"},
            )
            assert callback.status_code == 200
            assert callback.json()["status"] == "authorized"
            assert callback.json()["definition_key"] == "fake_identity"

            replay = client.get(
                f"/api/v1/organizations/{org_id}/integrations/oauth/callback",
                params={"state": state, "code": "sandbox-code"},
            )
            assert replay.status_code == 400

            expired = client.post(
                f"/api/v1/organizations/{org_id}/integrations/oauth/"
                "fake_identity/start",
                json={
                    "redirect_uri": "https://app.example.com/integrations/oauth/callback"
                },
            ).json()["state"]

            async def expire_state() -> None:
                async with database.session_factory() as session:
                    await session.execute(
                        update(IntegrationOAuthState)
                        .where(IntegrationOAuthState.consumed_at.is_(None))
                        .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
                    )
                    await session.commit()

            asyncio.run(expire_state())
            expired_callback = client.get(
                f"/api/v1/organizations/{org_id}/integrations/oauth/callback",
                params={"state": expired, "code": "sandbox-code"},
            )
            assert expired_callback.status_code == 400
    finally:
        app.dependency_overrides.clear()
