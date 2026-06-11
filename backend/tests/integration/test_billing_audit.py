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


def test_organization_billing_audit_run_and_tenant_boundary(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        use_llm=False,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'billing-audit.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id = _register(client, "owner@example.com", "Acme 中国")
            created = client.post(
                f"/api/v1/organizations/{org_id}/analysis-runs",
                json={
                    "source_hint": "csv",
                    "raw_text": """Transaction Date,Description,Amount,Currency
2026-05-01,OPENAI *CHATGPT SUBSCRIP,20.00,USD
2026-05-02,OPENAI *API,14.52,USD
2026-05-03,APPLE.COM/BILL,680,TWD
""",
                },
            )
            assert created.status_code == 201
            payload = created.json()
            assert payload["run"]["status"] == "completed"
            assert payload["run"]["items_count"] >= 2
            assert any(item["risk_type"] == "api_usage" for item in payload["items"])
            assert any(item["status"] == "apple_unresolved" for item in payload["items"])

            listed = client.get(f"/api/v1/organizations/{org_id}/analysis-runs")
            assert listed.status_code == 200
            assert listed.json()["items"][0]["id"] == payload["run"]["id"]

            detail = client.get(
                f"/api/v1/organizations/{org_id}/analysis-runs/{payload['run']['id']}"
            )
            assert detail.status_code == 200
            assert detail.json()["items"][0]["software_name"]

            client.post("/api/v1/auth/logout")
            other_org_id = _register(client, "other@example.com", "Other")
            assert (
                client.get(
                    f"/api/v1/organizations/{other_org_id}/analysis-runs/{payload['run']['id']}"
                ).status_code
                == 404
            )
    finally:
        app.dependency_overrides.clear()
