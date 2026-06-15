import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.outbox.models import OutboxEvent
from app.domains.status_page.models import StatusComponent, StatusIncident
from app.domains.status_page.service import StatusPageService
from app.main import app


def _client(database: Database, tmp_path: Path) -> TestClient:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'status.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


async def _publish_incident(database: Database) -> tuple[UUID, UUID]:
    async with database.session_factory() as session:
        component = StatusComponent(
            slug="integrations",
            name="集成与同步",
            description="第三方连接和同步任务",
            display_order=10,
        )
        session.add(component)
        await session.flush()
        incident = StatusIncident(
            status_component_id=component.id,
            title="部分同步任务延迟",
            public_summary="部分同步任务处理时间高于正常水平。",
            internal_summary="队列分片 shard-eu-03 积压，供应商令牌刷新异常。",
            impact="degraded",
        )
        published = await StatusPageService(session).publish_incident(
            incident,
            public_message="我们正在调查部分同步任务延迟。",
            internal_note="检查内部队列 shard-eu-03。",
            now=datetime(2026, 6, 15, 8, 0, tzinfo=UTC),
        )
        await session.commit()
        return component.id, published.id


def test_active_incident_degrades_component_and_resolve_restores_it(
    database: Database,
) -> None:
    async def exercise() -> None:
        component_id, incident_id = await _publish_incident(database)
        async with database.session_factory() as session:
            component = await session.get(StatusComponent, component_id)
            assert component is not None
            assert component.status == "degraded"

            service = StatusPageService(session)
            await service.add_incident_update(
                incident_id,
                status="identified",
                public_message="已经定位到同步队列拥堵，正在扩容处理。",
                internal_note="扩容 worker pool 到 12。",
                now=datetime(2026, 6, 15, 8, 15, tzinfo=UTC),
            )
            await service.add_incident_update(
                incident_id,
                status="monitoring",
                public_message="同步速度已经恢复，正在持续观察。",
                internal_note="观察积压曲线和令牌刷新失败率。",
                now=datetime(2026, 6, 15, 8, 45, tzinfo=UTC),
            )
            await service.add_incident_update(
                incident_id,
                status="resolved",
                public_message="同步延迟已经恢复，所有积压任务均已处理。",
                internal_note="根因记录到内部复盘文档。",
                now=datetime(2026, 6, 15, 9, 0, tzinfo=UTC),
            )
            await session.commit()

        async with database.session_factory() as session:
            component = await session.get(StatusComponent, component_id)
            incident = await session.get(StatusIncident, incident_id)
            assert component is not None
            assert incident is not None
            assert component.status == "operational"
            assert incident.status == "resolved"
            assert incident.resolved_at is not None

    asyncio.run(exercise())


def test_public_status_endpoints_hide_internal_details(
    database: Database,
    tmp_path: Path,
) -> None:
    component_id, incident_id = asyncio.run(_publish_incident(database))
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            overview = client.get("/api/v1/status")
            assert overview.status_code == 200
            payload = overview.json()
            assert payload["overall_status"] == "degraded"
            assert payload["components"][0]["id"] == str(component_id)
            assert payload["incidents"][0]["id"] == str(incident_id)
            assert "internal_summary" not in overview.text
            assert "shard-eu-03" not in overview.text

            incidents = client.get("/api/v1/status/incidents")
            assert incidents.status_code == 200
            assert incidents.json()["items"][0]["updates"][0]["status"] == "investigating"
            assert "internal_note" not in incidents.text
            assert "shard-eu-03" not in incidents.text
    finally:
        app.dependency_overrides.clear()


def test_status_subscription_is_idempotent_and_queues_confirmation(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            first = client.post(
                "/api/v1/status/subscriptions",
                json={"email": " Operations@example.com "},
            )
            second = client.post(
                "/api/v1/status/subscriptions",
                json={"email": "operations@example.com"},
            )
            assert first.status_code == 202
            assert second.status_code == 202
            assert first.json()["status"] == "confirmation_pending"
    finally:
        app.dependency_overrides.clear()

    async def confirmation_count() -> int:
        async with database.session_factory() as session:
            return int(
                await session.scalar(
                    select(func.count(OutboxEvent.id)).where(
                        OutboxEvent.event_type == "status.subscription_confirmation"
                    )
                )
                or 0
            )

    assert asyncio.run(confirmation_count()) == 1
