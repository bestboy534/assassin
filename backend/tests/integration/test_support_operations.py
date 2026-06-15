import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli import assign_platform_role
from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.outbox.models import OutboxEvent
from app.main import app


def _client(database: Database, tmp_path: Path) -> TestClient:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'support-operations.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _register(
    client: TestClient,
    email: str,
    organization_name: str,
) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "Operations User",
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


def _promote(database: Database, email: str, role: str) -> None:
    asyncio.run(
        assign_platform_role(
            email,
            role,
            database,
            reason="Support operations integration test",
        )
    )


def test_support_operator_replies_and_customer_reads_conversation(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            organization_id, _ = _register(
                client,
                "support-customer@example.com",
                "Support Customer",
            )
            created = client.post(
                "/api/v1/support/tickets",
                json={
                    "organization_id": organization_id,
                    "subject": "身份目录同步失败",
                    "description": "同步任务连续失败，请协助排查。",
                    "category": "integration",
                    "priority": "high",
                },
            )
            assert created.status_code == 201
            ticket_id = created.json()["id"]
            client.post(
                f"/api/v1/support/tickets/{ticket_id}/messages",
                json={"body": "错误从今天凌晨开始出现。"},
            )

            client.post("/api/v1/auth/logout")
            _register(client, "support-operator@example.com", "Support Operations")
            _promote(database, "support-operator@example.com", "support_agent")
            client.post("/api/v1/auth/logout")
            _login(client, "support-operator@example.com")

            session = client.get("/api/v1/auth/me")
            assert session.status_code == 200
            assert session.json()["user"]["platform_role"] == "support_agent"

            queue = client.get("/api/v1/support/operations/tickets")
            assert queue.status_code == 200
            assert queue.json()["items"][0]["id"] == ticket_id

            reply = client.post(
                f"/api/v1/support/operations/tickets/{ticket_id}/messages",
                json={"body": "我们已定位到连接令牌过期，请重新授权。"},
            )
            assert reply.status_code == 201
            assert reply.json()["author_type"] == "support"

            conversation = client.get(
                f"/api/v1/support/operations/tickets/{ticket_id}/messages"
            )
            assert conversation.status_code == 200
            assert [item["author_type"] for item in conversation.json()["items"]] == [
                "customer",
                "support",
            ]

            client.post("/api/v1/auth/logout")
            _login(client, "support-customer@example.com")
            customer_messages = client.get(
                f"/api/v1/support/tickets/{ticket_id}/messages"
            )
            assert customer_messages.status_code == 200
            assert customer_messages.json()["items"][-1]["body"].startswith(
                "我们已定位"
            )

            forbidden = client.get("/api/v1/support/operations/tickets")
            assert forbidden.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_platform_admin_publishes_status_incident_and_queues_update(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            _register(client, "status-admin@example.com", "Status Operations")
            _promote(database, "status-admin@example.com", "platform_admin")
            client.post("/api/v1/auth/logout")
            _login(client, "status-admin@example.com")

            component = client.post(
                "/api/v1/admin/status/components",
                json={
                    "slug": "integrations",
                    "name": "集成与同步",
                    "description": "第三方连接与同步任务",
                    "display_order": 10,
                },
            )
            assert component.status_code == 201

            incident = client.post(
                "/api/v1/admin/status/incidents",
                json={
                    "component_id": component.json()["id"],
                    "title": "部分同步任务延迟",
                    "public_summary": "部分同步任务处理时间高于正常水平。",
                    "internal_summary": "队列分片积压。",
                    "impact": "degraded",
                    "public_message": "我们正在调查同步任务延迟。",
                    "internal_note": "检查内部队列。",
                },
            )
            assert incident.status_code == 201
            assert incident.json()["status"] == "investigating"

            public = client.get("/api/v1/status")
            assert public.status_code == 200
            assert public.json()["overall_status"] == "degraded"
            assert public.json()["incidents"][0]["title"] == "部分同步任务延迟"
            assert "队列分片积压" not in public.text
    finally:
        app.dependency_overrides.clear()

    async def notification_count() -> int:
        async with database.session_factory() as session:
            return int(
                await session.scalar(
                    select(func.count(OutboxEvent.id)).where(
                        OutboxEvent.event_type == "status.incident_updated"
                    )
                )
                or 0
            )

    assert asyncio.run(notification_count()) == 1
