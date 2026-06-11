import asyncio
from collections.abc import AsyncIterator
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.organizations.models import OrganizationMember
from app.main import app


def _register(
    client: TestClient,
    email: str,
    organization: str,
) -> tuple[str, str]:
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
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


def test_vendor_risk_flow_is_explainable_permissioned_and_tenant_scoped(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'vendors.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id, _ = _register(client, "owner@example.com", "Acme 中国")
            created = client.post(
                f"/api/v1/organizations/{org_id}/vendors",
                json={
                    "name": "Adobe",
                    "domain": "adobe.com",
                    "country_code": "US",
                    "category": "创意软件",
                    "business_owner": "设计团队",
                    "risk_owner": "安全负责人",
                },
            )
            assert created.status_code == 201
            vendor_id = created.json()["id"]
            assert created.json()["status"] == "active"

            alias = client.post(
                f"/api/v1/organizations/{org_id}/vendors/{vendor_id}/aliases",
                json={"alias": "ADOBE *CREATIVE CLOUD"},
            )
            assert alias.status_code == 201
            matched = client.get(
                f"/api/v1/organizations/{org_id}/vendors/match",
                params={"name": "Adobe Creative Cloud"},
            )
            assert matched.status_code == 200
            assert matched.json()["id"] == vendor_id

            assessment = client.post(
                f"/api/v1/organizations/{org_id}/vendors/{vendor_id}/assessments",
                json={
                    "questionnaire_version": 1,
                    "has_soc2": False,
                    "has_iso27001": False,
                    "has_dpa": False,
                    "supports_sso": False,
                    "has_incident_response": False,
                    "financial_stability": "weak",
                    "service_criticality": "high",
                    "stores_sensitive_data": True,
                },
            )
            assert assessment.status_code == 201
            assessment_payload = assessment.json()
            assert assessment_payload["assessment"]["total_score"] == 82
            assert assessment_payload["assessment"]["rule_version"] == "vendor-risk-v1"
            assert assessment_payload["assessment"]["dimensions"]["security"]["score"] == 80
            assert assessment_payload["assessment"]["dimensions"]["privacy"]["reasons"]
            assert len(assessment_payload["findings"]) == 5
            finding_id = assessment_payload["findings"][0]["id"]

            latest = client.get(
                f"/api/v1/organizations/{org_id}/vendors/{vendor_id}/assessments/latest"
            )
            assert latest.status_code == 200
            assert latest.json()["item"]["assessment"]["total_score"] == 82
            assert len(latest.json()["item"]["findings"]) == 5

            findings = client.get(f"/api/v1/organizations/{org_id}/risk-findings")
            assert findings.status_code == 200
            assert len(findings.json()["items"]) == 5

            client.post("/api/v1/auth/logout")
            other_org_id, member_user_id = _register(
                client,
                "member@example.com",
                "Other",
            )
            assert (
                client.get(
                    f"/api/v1/organizations/{other_org_id}/vendors/{vendor_id}"
                ).status_code
                == 404
            )

            async def add_member_to_first_organization() -> None:
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

            asyncio.run(add_member_to_first_organization())
            expires_at = (date.today() + timedelta(days=180)).isoformat()
            forbidden = client.post(
                f"/api/v1/organizations/{org_id}/risk-findings/{finding_id}/accept",
                json={
                    "reason": "业务例外需要临时接受",
                    "expires_at": expires_at,
                    "risk_owner": "安全负责人",
                },
            )
            assert forbidden.status_code == 403

            client.post("/api/v1/auth/logout")
            login = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "owner@example.com",
                    "password": "Long passphrase 2026!",
                },
            )
            assert login.status_code == 200
            accepted = client.post(
                f"/api/v1/organizations/{org_id}/risk-findings/{finding_id}/accept",
                json={
                    "reason": "合同期限内接受，已安排替代方案评估。",
                    "expires_at": expires_at,
                    "risk_owner": "安全负责人",
                },
            )
            assert accepted.status_code == 200
            assert accepted.json()["status"] == "accepted"
            assert accepted.json()["accepted_reason"].startswith("合同期限内接受")
    finally:
        app.dependency_overrides.clear()
