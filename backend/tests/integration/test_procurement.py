import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.procurement.models import ApprovalDecision
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


def test_purchase_request_submit_approval_and_tenant_boundary(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'procurement.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id = _register(client, "owner@example.com", "Acme 中国")
            invalid = client.post(
                f"/api/v1/organizations/{org_id}/purchase-requests",
                json={
                    "software_name": "Notion AI",
                    "business_reason": "团队知识库需要 AI 总结能力",
                    "estimated_monthly_cost_usd": 120,
                    "department": "运营",
                    "handles_sensitive_data": True,
                    "data_categories": [],
                },
            )
            assert invalid.status_code == 422

            created = client.post(
                f"/api/v1/organizations/{org_id}/purchase-requests",
                json={
                    "software_name": "Notion AI",
                    "business_reason": "团队知识库需要 AI 总结能力",
                    "estimated_monthly_cost_usd": 120,
                    "department": "运营",
                    "handles_sensitive_data": True,
                    "data_categories": ["客户资料", "内部文档"],
                },
            )
            assert created.status_code == 201
            request_id = created.json()["id"]
            assert created.json()["status"] == "draft"

            submitted = client.post(
                f"/api/v1/organizations/{org_id}/purchase-requests/{request_id}/submit"
            )
            assert submitted.status_code == 200
            assert submitted.json()["status"] == "in_review"

            tasks = client.get(f"/api/v1/organizations/{org_id}/approval-tasks")
            assert tasks.status_code == 200
            task = tasks.json()["items"][0]
            assert task["purchase_request_id"] == request_id
            assert task["status"] == "pending"

            headers = {"Idempotency-Key": "approve-notion-ai"}
            first = client.post(
                f"/api/v1/organizations/{org_id}/approval-tasks/{task['id']}/approve",
                headers=headers,
                json={"comment": "预算和用途都清楚，同意采购。"},
            )
            second = client.post(
                f"/api/v1/organizations/{org_id}/approval-tasks/{task['id']}/approve",
                headers=headers,
                json={"comment": "重复点击不应新增决定。"},
            )
            assert first.status_code == 200
            assert second.status_code == 200
            assert second.json()["status"] == "approved"

            detail = client.get(f"/api/v1/organizations/{org_id}/purchase-requests/{request_id}")
            assert detail.status_code == 200
            assert detail.json()["status"] == "approved"

        async def decision_count() -> int:
            async with database.session_factory() as session:
                decisions = (
                    await session.scalars(
                        select(ApprovalDecision).where(
                            ApprovalDecision.idempotency_key == "approve-notion-ai"
                        )
                    )
                ).all()
                return len(decisions)

        assert asyncio.run(decision_count()) == 1

        with TestClient(app) as client:
            other_org_id = _register(client, "other@example.com", "Other")
            assert (
                client.get(
                    f"/api/v1/organizations/{other_org_id}/purchase-requests/{request_id}"
                ).status_code
                == 404
            )
    finally:
        app.dependency_overrides.clear()
