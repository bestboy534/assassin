import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.outbox.models import OutboxEvent
from app.domains.support.models import SupportAccessLog, SupportGrant, SupportTicket
from app.domains.support.service import (
    SupportAccessService,
    SupportPermissionDenied,
    SupportTicketService,
)
from app.main import app


def _client(database: Database, tmp_path: Path) -> TestClient:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'support.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _register(
    client: TestClient,
    *,
    email: str,
    organization_name: str,
) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "Support User",
            "organization_name": organization_name,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Long passphrase 2026!"},
    )
    assert response.status_code == 200


def test_support_ticket_lifecycle_is_tenant_scoped(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            organization_id, _ = _register(
                client,
                email="ticket-owner@example.com",
                organization_name="Ticket Org",
            )
            created = client.post(
                "/api/v1/support/tickets",
                json={
                    "organization_id": organization_id,
                    "subject": "同步任务持续失败",
                    "description": "身份目录同步连续三次失败，需要协助诊断。",
                    "category": "integration",
                    "priority": "high",
                },
            )
            assert created.status_code == 201
            ticket = created.json()
            assert ticket["status"] == "new"
            assert ticket["first_response_due_at"] < ticket["resolution_due_at"]

            listed = client.get(
                "/api/v1/support/tickets",
                params={"organization_id": organization_id},
            )
            assert listed.status_code == 200
            assert [item["id"] for item in listed.json()["items"]] == [ticket["id"]]

            async def queue_sla_warning_twice() -> int:
                warning_time = datetime.now(UTC)
                async with database.session_factory() as session:
                    stored = await session.get(SupportTicket, UUID(ticket["id"]))
                    assert stored is not None
                    stored.resolution_due_at = warning_time + timedelta(minutes=30)
                    await session.commit()
                for _ in range(2):
                    async with database.session_factory() as session:
                        await SupportTicketService(session).queue_sla_warnings(
                            now=warning_time
                        )
                        await session.commit()
                async with database.session_factory() as session:
                    return int(
                        await session.scalar(
                            select(func.count(OutboxEvent.id)).where(
                                OutboxEvent.event_type == "support.sla_warning",
                                OutboxEvent.aggregate_id
                                == f"{ticket['id']}:resolution",
                            )
                        )
                        or 0
                    )

            assert asyncio.run(queue_sla_warning_twice()) == 1

            message = client.post(
                f"/api/v1/support/tickets/{ticket['id']}/messages",
                json={"body": "补充：失败发生在凌晨同步窗口。"},
            )
            assert message.status_code == 201
            assert message.json()["author_type"] == "customer"

            waiting = client.patch(
                f"/api/v1/support/tickets/{ticket['id']}",
                json={"status": "waiting_customer"},
            )
            assert waiting.status_code == 200
            assert waiting.json()["sla_paused_at"] is not None

            resolved = client.post(
                f"/api/v1/support/tickets/{ticket['id']}/resolve",
                json={"resolution": "已重新建立连接并完成一次全量同步。"},
            )
            assert resolved.status_code == 200
            assert resolved.json()["status"] == "resolved"

            satisfaction = client.post(
                f"/api/v1/support/tickets/{ticket['id']}/satisfaction",
                json={"rating": 5, "comment": "处理清楚且及时。"},
            )
            assert satisfaction.status_code == 201
            assert satisfaction.json()["rating"] == 5

            client.post("/api/v1/auth/logout")
            _register(
                client,
                email="other-ticket@example.com",
                organization_name="Other Ticket Org",
            )
            hidden = client.get(f"/api/v1/support/tickets/{ticket['id']}")
            assert hidden.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_customer_approved_support_grant_is_scoped_audited_and_revocable(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            organization_id, _ = _register(
                client,
                email="grant-owner@example.com",
                organization_name="Grant Org",
            )
            client.post("/api/v1/auth/logout")
            _, support_user_id = _register(
                client,
                email="support-agent@example.com",
                organization_name="Support Team",
            )
            client.post("/api/v1/auth/logout")
            _login(client, "grant-owner@example.com")

            expires_at = datetime.now(UTC) + timedelta(hours=2)
            created = client.post(
                f"/api/v1/organizations/{organization_id}/support-grants",
                json={
                    "support_user_id": support_user_id,
                    "scopes": [
                        "configuration.read",
                        "sync_diagnostics.read",
                        "job_logs.read",
                    ],
                    "reason": "排查身份目录同步错误",
                    "expires_at": expires_at.isoformat(),
                },
            )
            assert created.status_code == 201
            grant = created.json()
            assert grant["scopes"] == [
                "configuration.read",
                "sync_diagnostics.read",
                "job_logs.read",
            ]

            client.post("/api/v1/auth/logout")
            _login(client, "support-agent@example.com")
            diagnostics = client.post(
                f"/api/v1/support/grants/{grant['id']}/diagnostics",
                json={"purpose": "确认最近同步任务的错误摘要"},
            )
            assert diagnostics.status_code == 200
            assert diagnostics.json()["grant_id"] == grant["id"]
            assert "business_records" not in diagnostics.text

            async def access_log_count() -> int:
                async with database.session_factory() as session:
                    return int(
                        await session.scalar(
                            select(func.count(SupportAccessLog.id)).where(
                                SupportAccessLog.support_grant_id
                                == UUID(grant["id"])
                            )
                        )
                        or 0
                    )

            assert asyncio.run(access_log_count()) == 1

            client.post("/api/v1/auth/logout")
            _login(client, "grant-owner@example.com")
            revoked = client.post(
                f"/api/v1/organizations/{organization_id}/support-grants/{grant['id']}/revoke"
            )
            assert revoked.status_code == 200
            assert revoked.json()["revoked_at"] is not None

            client.post("/api/v1/auth/logout")
            _login(client, "support-agent@example.com")
            blocked = client.post(
                f"/api/v1/support/grants/{grant['id']}/diagnostics",
                json={"purpose": "再次读取"},
            )
            assert blocked.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_expired_support_grant_blocks_diagnostic_access(
    database: Database,
) -> None:
    organization_id = UUID("00000000-0000-0000-0000-000000000011")
    support_user_id = UUID("00000000-0000-0000-0000-000000000012")
    approver_id = UUID("00000000-0000-0000-0000-000000000013")
    async with database.session_factory() as session:
        grant = SupportGrant(
            organization_id=organization_id,
            support_user_id=support_user_id,
            scopes_json=["sync_diagnostics.read"],
            reason="Expired diagnostic window",
            approved_by_user_id=approver_id,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        session.add(grant)
        await session.commit()

        with pytest.raises(SupportPermissionDenied):
            await SupportAccessService(session).read_sync_diagnostics(
                grant.id,
                support_user_id=support_user_id,
                purpose="Expired access attempt",
            )
