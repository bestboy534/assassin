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
            "display_name": "优化负责人",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    return response.json()["organizations"][0]["id"]


def test_savings_opportunity_project_realization_and_verification(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'savings.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id = _register(client, "owner@example.com", "Acme 中国")
            payload = {
                "source_type": "analysis_item",
                "source_id": "sub-notion-2026-06",
                "rule_version": "idle-subscription-v1",
                "period_key": "2026-06",
                "title": "取消闲置 Notion 订阅",
                "department": "运营",
                "category": "cancellation",
                "monthly_baseline": "100.0000",
                "currency": "USD",
                "effective_date": "2026-07-01",
                "contract_end": "2026-12-31",
                "evidence": "连续 60 天无活跃使用记录",
            }
            created = client.post(
                f"/api/v1/organizations/{org_id}/savings-opportunities",
                json=payload,
            )
            assert created.status_code == 201
            opportunity = created.json()
            opportunity_id = opportunity["id"]
            assert opportunity["status"] == "new"
            assert opportunity["estimated_amount"] == "600.0000"
            assert opportunity["baseline"]["calculation_method"] == "remaining_term"

            duplicate = client.post(
                f"/api/v1/organizations/{org_id}/savings-opportunities",
                json=payload,
            )
            assert duplicate.status_code == 201
            assert duplicate.json()["id"] == opportunity_id

            unsupported_currency = client.post(
                f"/api/v1/organizations/{org_id}/savings-opportunities",
                json={
                    **payload,
                    "source_id": "sub-notion-eur-2026-06",
                    "currency": "EUR",
                },
            )
            assert unsupported_currency.status_code == 422

            listed = client.get(
                f"/api/v1/organizations/{org_id}/savings-opportunities"
            )
            assert listed.status_code == 200
            assert len(listed.json()["items"]) == 1

            confirmed = client.post(
                f"/api/v1/organizations/{org_id}/savings-opportunities/"
                f"{opportunity_id}/confirm"
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["status"] == "confirmed"

            project = client.post(
                f"/api/v1/organizations/{org_id}/savings-opportunities/"
                f"{opportunity_id}/projects",
                json={
                    "owner_name": "运营负责人",
                    "due_date": "2026-07-31",
                },
            )
            assert project.status_code == 201
            project_body = project.json()
            project_id = project_body["project"]["id"]
            assert project_body["project"]["target_amount"] == "600.0000"
            assert project_body["tasks"][0]["title"] == "确认取消路径与负责人"

            projects = client.get(
                f"/api/v1/organizations/{org_id}/optimization-projects"
            )
            assert projects.status_code == 200
            assert projects.json()["items"][0]["project"]["id"] == project_id

            realized = client.post(
                f"/api/v1/organizations/{org_id}/optimization-projects/"
                f"{project_id}/realize",
                json={
                    "action": "cancelled",
                    "effective_date": "2026-07-01",
                    "new_monthly_cost": "0.0000",
                    "evidence": "供应商确认已在 2026-07-01 取消",
                },
            )
            assert realized.status_code == 200
            assert realized.json()["result"]["status"] == "realized"
            assert realized.json()["result"]["realized_amount"] == "600.0000"

            summary_before_verification = client.get(
                f"/api/v1/organizations/{org_id}/savings-summary"
            )
            assert summary_before_verification.status_code == 200
            assert summary_before_verification.json()["estimated"] == "600.0000"
            assert summary_before_verification.json()["realized"] == "600.0000"
            assert summary_before_verification.json()["verified"] == "0.0000"

            missing_evidence = client.post(
                f"/api/v1/organizations/{org_id}/optimization-projects/"
                f"{project_id}/verify",
                json={"evidence_references": []},
            )
            assert missing_evidence.status_code == 422

            verified = client.post(
                f"/api/v1/organizations/{org_id}/optimization-projects/"
                f"{project_id}/verify",
                json={"evidence_references": ["transaction:txn-2026-08-notion"]},
            )
            assert verified.status_code == 200
            assert verified.json()["result"]["status"] == "verified"
            assert verified.json()["result"]["verified_amount"] == "600.0000"

            summary = client.get(
                f"/api/v1/organizations/{org_id}/savings-summary"
            )
            assert summary.status_code == 200
            assert summary.json() == {
                "currency": "USD",
                "estimated": "600.0000",
                "realized": "600.0000",
                "verified": "600.0000",
                "cost_avoidance": "0.0000",
            }

            client.post("/api/v1/auth/logout")
            other_org_id = _register(client, "other@example.com", "Other")
            tenant_items = client.get(
                f"/api/v1/organizations/{other_org_id}/savings-opportunities"
            )
            assert tenant_items.status_code == 200
            assert tenant_items.json()["items"] == []
    finally:
        app.dependency_overrides.clear()
