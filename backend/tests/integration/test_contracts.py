from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.contracts.models import Renewal
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


def test_renewal_source_version_has_foreign_key() -> None:
    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in Renewal.__table__.c.source_version_id.foreign_keys
    }
    assert foreign_keys == {"contract_versions.id"}


def test_signed_contract_creates_renewal_and_is_immutable(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'contracts.db'}",
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
                f"/api/v1/organizations/{org_id}/contracts",
                json={
                    "name": "Notion 企业版 2026",
                    "vendor_name": "Notion Labs",
                    "application_name": "Notion",
                    "owner_name": "运营负责人",
                    "start_date": "2026-02-01",
                    "end_date": "2027-01-31",
                    "amount": 12000,
                    "currency": "USD",
                    "billing_frequency": "yearly",
                    "auto_renew": True,
                    "notice_period_days": 60,
                },
            )
            assert created.status_code == 201
            payload = created.json()
            contract_id = payload["contract"]["id"]
            version_id = payload["version"]["id"]
            assert payload["contract"]["status"] == "draft"
            assert payload["version"]["status"] == "draft"
            assert payload["contract"]["current_version_id"] == version_id

            signed = client.post(
                f"/api/v1/organizations/{org_id}/contracts/{contract_id}/versions/{version_id}/mark-signed"
            )
            assert signed.status_code == 200
            signed_payload = signed.json()
            assert signed_payload["contract"]["status"] == "active"
            assert signed_payload["version"]["status"] == "signed"
            assert signed_payload["renewal"]["renewal_date"] == "2027-01-31"
            assert signed_payload["renewal"]["decision_deadline"] == "2026-12-02"

            signed_again = client.post(
                f"/api/v1/organizations/{org_id}/contracts/{contract_id}/versions/{version_id}/mark-signed"
            )
            assert signed_again.status_code == 200
            assert signed_again.json()["renewal"]["id"] == signed_payload["renewal"]["id"]

            immutable = client.patch(
                f"/api/v1/organizations/{org_id}/contracts/{contract_id}/versions/{version_id}",
                json={"amount": 9000},
            )
            assert immutable.status_code == 409

            renewals = client.get(f"/api/v1/organizations/{org_id}/renewals")
            assert renewals.status_code == 200
            assert len(renewals.json()["items"]) == 1
            assert renewals.json()["items"][0]["contract_id"] == contract_id
            assert renewals.json()["items"][0]["status"] == "upcoming"

            client.post("/api/v1/auth/logout")
            other_org_id = _register(client, "other@example.com", "Other")
            assert (
                client.get(
                    f"/api/v1/organizations/{other_org_id}/contracts/{contract_id}"
                ).status_code
                == 404
            )
    finally:
        app.dependency_overrides.clear()
