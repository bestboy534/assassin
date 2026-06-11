from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.main import app


def _register(client: TestClient, email: str, organization: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "负责人",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    return response.json()["organizations"][0]["id"]


def test_application_catalog_crud_and_tenant_boundary(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'apps.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id = _register(client, "owner@example.com", "Acme 中国")
            create = client.post(
                f"/api/v1/organizations/{org_id}/applications",
                json={"name": "Notion", "category": "协作", "business_owner": "运营"},
            )
            assert create.status_code == 201
            application_id = create.json()["id"]

            duplicate = client.post(
                f"/api/v1/organizations/{org_id}/applications",
                json={"name": " notion ", "category": "协作"},
            )
            assert duplicate.status_code == 409

            listed = client.get(f"/api/v1/organizations/{org_id}/applications")
            assert listed.status_code == 200
            assert listed.json()["items"][0]["name"] == "Notion"

            updated = client.patch(
                f"/api/v1/organizations/{org_id}/applications/{application_id}",
                json={"approved": True, "risk_level": "low"},
            )
            assert updated.status_code == 200
            assert updated.json()["approved"] is True

            client.post("/api/v1/auth/logout")
            other_org_id = _register(client, "other@example.com", "Other")
            assert (
                client.get(f"/api/v1/organizations/{org_id}/applications/{application_id}").status_code
                == 404
            )
            assert client.get(f"/api/v1/organizations/{other_org_id}/applications").json() == {
                "items": []
            }
    finally:
        app.dependency_overrides.clear()
