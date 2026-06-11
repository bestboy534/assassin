from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.main import app


def test_register_creates_owner_workspace_and_session(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'identity.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": " Owner@Example.COM ",
                    "password": "Long passphrase 2026!",
                    "display_name": "负责人",
                    "organization_name": "Acme 中国",
                },
            )
            assert response.status_code == 201
            assert response.json()["user"]["email"] == "owner@example.com"
            assert response.json()["organizations"][0]["role"] == "owner"
            assert "HttpOnly" in response.headers["set-cookie"]
            assert "samesite=lax" in response.headers["set-cookie"].casefold()

            me = client.get("/api/v1/auth/me")
            assert me.status_code == 200
            assert me.json()["organizations"][0]["name"] == "Acme 中国"

            created = client.post("/api/v1/organizations", json={"name": "第二工作区"})
            assert created.status_code == 201
            assert created.json()["role"] == "owner"

            listed = client.get("/api/v1/organizations")
            assert listed.status_code == 200
            assert len(listed.json()["items"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_login_logout_and_tenant_404(database: Database, tmp_path: Path) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'identity-tenant.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            assert (
                client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "owner@example.com",
                        "password": "Long passphrase 2026!",
                        "display_name": "负责人",
                    },
                ).status_code
                == 201
            )
            assert client.post("/api/v1/auth/logout").status_code == 200
            assert client.get("/api/v1/auth/me").status_code == 401

            login = client.post(
                "/api/v1/auth/login",
                json={"email": "OWNER@example.com", "password": "Long passphrase 2026!"},
            )
            assert login.status_code == 200
            assert client.get(f"/api/v1/organizations/{uuid4()}").status_code == 404
    finally:
        app.dependency_overrides.clear()
