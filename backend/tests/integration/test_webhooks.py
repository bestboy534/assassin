import asyncio
import hashlib
import hmac
import json
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.organizations.models import OrganizationMember
from app.domains.webhooks.delivery import (
    WebhookDeliveryService,
    WebhookSender,
    WebhookSendResult,
)
from app.domains.webhooks.models import WebhookDelivery, WebhookEndpoint
from app.domains.webhooks.router import webhook_sender_from_request
from app.domains.webhooks.service import WebhookService
from app.infrastructure.secrets import LocalSecretCipher
from app.main import app


class RecordingSender(WebhookSender):
    def __init__(self, statuses: list[int]) -> None:
        self.statuses = list(statuses)
        self.requests: list[tuple[str, Mapping[str, str], bytes]] = []

    async def send(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
    ) -> WebhookSendResult:
        self.requests.append((url, dict(headers), body))
        status = self.statuses.pop(0)
        return WebhookSendResult(status_code=status, response_body="recorded")


def _client(
    database: Database,
    tmp_path: Path,
    sender: WebhookSender,
) -> TestClient:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'webhooks.db'}",
        webhook_secret_key="test-webhook-secret",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[webhook_sender_from_request] = lambda: sender
    return TestClient(app)


def _register(
    client: TestClient,
    *,
    email: str = "webhook-owner@example.com",
    organization: str = "Webhook 组织",
) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "Webhook 管理员",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


def _assert_signature(
    secret: str,
    headers: Mapping[str, str],
    body: bytes,
) -> None:
    timestamp = headers["X-Webhook-Timestamp"]
    expected = hmac.new(
        secret.encode(),
        timestamp.encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    assert headers["X-Webhook-Signature"] == f"v1={expected}"


def test_webhook_secret_is_one_time_and_rotation_preserves_inflight_signing(
    database: Database,
    tmp_path: Path,
) -> None:
    sender = RecordingSender([200, 200])
    client_context = _client(database, tmp_path, sender)
    try:
        with client_context as client:
            organization_id, _ = _register(client)
            created = client.post(
                f"/api/v1/organizations/{organization_id}/webhooks",
                json={
                    "name": "数据仓库",
                    "url": "https://hooks.example.test/events",
                    "events": ["report.exported", "invoice.approved"],
                },
            )
            assert created.status_code == 201
            endpoint_id = created.json()["id"]
            old_secret = created.json()["secret"]

            listed = client.get(
                f"/api/v1/organizations/{organization_id}/webhooks"
            )
            assert listed.status_code == 200
            assert old_secret not in listed.text
            assert "ciphertext" not in listed.text

            async def enqueue_old_event() -> UUID:
                async with database.session_factory() as session:
                    service = WebhookService(
                        session,
                        LocalSecretCipher("test-webhook-secret"),
                    )
                    deliveries = await service.publish_event(
                        organization_id=UUID(organization_id),
                        event_id=uuid4(),
                        event_type="report.exported",
                        payload={"report_id": "report-1"},
                    )
                    assert len(deliveries) == 1
                    return deliveries[0].id

            old_delivery_id = asyncio.run(enqueue_old_event())

            rotated = client.post(
                f"/api/v1/organizations/{organization_id}/webhooks/"
                f"{endpoint_id}/rotate-secret",
                json={"overlap_seconds": 600},
            )
            assert rotated.status_code == 200
            new_secret = rotated.json()["secret"]
            assert new_secret != old_secret
            assert rotated.json()["previous_secret_expires_at"] is not None

            old_delivery = client.post(
                f"/api/v1/organizations/{organization_id}/webhooks/"
                f"{endpoint_id}/deliveries/{old_delivery_id}/retry"
            )
            assert old_delivery.status_code == 200
            assert old_delivery.json()["status"] == "delivered"
            _, old_headers, old_body = sender.requests[0]
            _assert_signature(old_secret, old_headers, old_body)
            assert json.loads(old_body)["data"]["report_id"] == "report-1"

            test_delivery = client.post(
                f"/api/v1/organizations/{organization_id}/webhooks/"
                f"{endpoint_id}/test",
                json={
                    "event_type": "invoice.approved",
                    "payload": {"invoice_id": "invoice-1"},
                },
            )
            assert test_delivery.status_code == 201
            assert test_delivery.json()["status"] == "delivered"
            _, new_headers, new_body = sender.requests[1]
            _assert_signature(new_secret, new_headers, new_body)
            assert json.loads(new_body)["data"]["invoice_id"] == "invoice-1"

            missing = client.post(
                f"/api/v1/organizations/{organization_id}/webhooks/"
                f"{uuid4()}/test",
                json={
                    "event_type": "invoice.approved",
                    "payload": {"invoice_id": "missing"},
                },
            )
            assert missing.status_code == 404

            client.post("/api/v1/auth/logout")
            _, member_user_id = _register(
                client,
                email="webhook-member@example.com",
                organization="成员自己的组织",
            )

            async def add_member() -> None:
                async with database.session_factory() as session:
                    session.add(
                        OrganizationMember(
                            organization_id=UUID(organization_id),
                            user_id=UUID(member_user_id),
                            role="member",
                            status="active",
                        )
                    )
                    await session.commit()

            asyncio.run(add_member())
            forbidden = client.post(
                f"/api/v1/organizations/{organization_id}/webhooks/"
                f"{endpoint_id}/test",
                json={
                    "event_type": "invoice.approved",
                    "payload": {"invoice_id": "forbidden"},
                },
            )
            assert forbidden.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_webhook_delivery_retries_then_moves_to_dead_letter(
    database: Database,
) -> None:
    async def run() -> None:
        organization_id = uuid4()
        user_id = uuid4()
        cipher = LocalSecretCipher("test-webhook-secret")
        sender = RecordingSender([503, 503, 503])
        async with database.session_factory() as session:
            service = WebhookService(session, cipher)
            endpoint, _ = await service.create_endpoint(
                organization_id=organization_id,
                created_by_user_id=user_id,
                name="失败端点",
                url="https://hooks.example.test/fail",
                events=["security.incident.created"],
            )
            deliveries = await service.publish_event(
                organization_id=organization_id,
                event_id=uuid4(),
                event_type="security.incident.created",
                payload={"incident_id": "incident-1"},
            )
            delivery_id = deliveries[0].id
            delivery_service = WebhookDeliveryService(session, cipher, sender)

            first = await delivery_service.deliver(
                organization_id,
                endpoint.id,
                delivery_id,
                now=datetime.now(UTC),
                max_attempts=3,
            )
            assert first.status == "pending"
            assert first.attempts == 1
            assert first.next_attempt_at is not None

            second = await delivery_service.deliver(
                organization_id,
                endpoint.id,
                delivery_id,
                now=datetime.now(UTC) + timedelta(minutes=5),
                max_attempts=3,
            )
            assert second.status == "pending"
            assert second.attempts == 2

            third = await delivery_service.deliver(
                organization_id,
                endpoint.id,
                delivery_id,
                now=datetime.now(UTC) + timedelta(minutes=10),
                max_attempts=3,
            )
            assert third.status == "dead_letter"
            assert third.attempts == 3
            assert third.last_error == "HTTP 503"

        async with database.session_factory() as session:
            endpoint_record = await session.get(WebhookEndpoint, endpoint.id)
            delivery_record = await session.scalar(
                select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
            )
            assert endpoint_record is not None
            assert endpoint_record.secret_ciphertext != ""
            assert delivery_record is not None
            assert delivery_record.status == "dead_letter"

    asyncio.run(run())


def test_webhook_delivery_worker_processes_only_due_attempts(
    database: Database,
) -> None:
    async def run() -> None:
        organization_id = uuid4()
        user_id = uuid4()
        cipher = LocalSecretCipher("test-webhook-secret")
        sender = RecordingSender([200])
        async with database.session_factory() as session:
            service = WebhookService(session, cipher)
            await service.create_endpoint(
                organization_id=organization_id,
                created_by_user_id=user_id,
                name="自动投递端点",
                url="https://hooks.example.test/worker",
                events=["report.exported"],
            )
            due = await service.publish_event(
                organization_id=organization_id,
                event_id=uuid4(),
                event_type="report.exported",
                payload={"report_id": "due"},
            )
            future = await service.publish_event(
                organization_id=organization_id,
                event_id=uuid4(),
                event_type="report.exported",
                payload={"report_id": "future"},
            )
            processing_time = datetime.now(UTC) + timedelta(seconds=1)
            future[0].next_attempt_at = processing_time + timedelta(hours=1)
            await session.commit()

            delivered = await WebhookDeliveryService(
                session,
                cipher,
                sender,
            ).deliver_due(now=processing_time, limit=10)

            assert [item.id for item in delivered] == [due[0].id]
            assert delivered[0].status == "delivered"
            assert len(sender.requests) == 1

    asyncio.run(run())
