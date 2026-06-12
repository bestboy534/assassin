import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
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
            "display_name": "支付负责人",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    return response.json()["organizations"][0]["id"]


def _create_purchase(client: TestClient, organization_id: str) -> str:
    response = client.post(
        f"/api/v1/organizations/{organization_id}/purchase-requests",
        json={
            "software_name": "Notion 企业版",
            "business_reason": "团队知识库与项目协作",
            "estimated_monthly_cost_usd": 120,
            "department": "运营",
            "handles_sensitive_data": False,
            "data_categories": [],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _approve_purchase(
    client: TestClient,
    organization_id: str,
    purchase_request_id: str,
) -> None:
    submitted = client.post(
        f"/api/v1/organizations/{organization_id}/purchase-requests/"
        f"{purchase_request_id}/submit"
    )
    assert submitted.status_code == 200
    tasks = client.get(
        f"/api/v1/organizations/{organization_id}/approval-tasks"
    ).json()["items"]
    approved = client.post(
        f"/api/v1/organizations/{organization_id}/approval-tasks/"
        f"{tasks[0]['id']}/approve",
        headers={"Idempotency-Key": f"approve-{purchase_request_id}"},
        json={"comment": "预算已确认，同意创建受控支付工具。"},
    )
    assert approved.status_code == 200


def _signed_webhook(secret: str, payload: dict[str, object]) -> tuple[dict[str, str], bytes]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(datetime.now(UTC).timestamp()))
    signature = hmac.new(
        secret.encode(),
        timestamp.encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return (
        {
            "X-Payment-Timestamp": timestamp,
            "X-Payment-Signature": signature,
            "Content-Type": "application/json",
        },
        body,
    )


def test_approved_purchase_virtual_card_webhook_and_reconciliation(
    database: Database,
    tmp_path: Path,
) -> None:
    webhook_secret = "test-payment-webhook-secret"
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'payments.db'}",
        payment_provider="fake",
        payment_webhook_secret=webhook_secret,
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id = _register(client, "owner@example.com", "Acme 中国")
            purchase_id = _create_purchase(client, org_id)
            card_payload = {
                "purchase_request_id": purchase_id,
                "owner_name": "运营负责人",
                "merchant_lock": "Notion Labs",
                "currency": "USD",
                "limits": {
                    "single": "300.0000",
                    "daily": "500.0000",
                    "monthly": "1200.0000",
                    "total": "12000.0000",
                },
            }

            unapproved = client.post(
                f"/api/v1/organizations/{org_id}/payment-instruments",
                headers={"Idempotency-Key": "card-notion-2026"},
                json=card_payload,
            )
            assert unapproved.status_code == 409

            _approve_purchase(client, org_id, purchase_id)
            created = client.post(
                f"/api/v1/organizations/{org_id}/payment-instruments",
                headers={"Idempotency-Key": "card-notion-2026"},
                json=card_payload,
            )
            duplicate = client.post(
                f"/api/v1/organizations/{org_id}/payment-instruments",
                headers={"Idempotency-Key": "card-notion-2026"},
                json=card_payload,
            )
            assert created.status_code == 201
            assert duplicate.status_code == 201
            card = created.json()
            instrument_id = card["instrument"]["id"]
            external_id = card["instrument"]["external_id"]
            assert duplicate.json()["instrument"]["id"] == instrument_id
            assert card["instrument"]["status"] == "active"
            assert card["instrument"]["last4"] == "4242"
            assert card["instrument"]["sandbox"] is True
            assert "card_number" not in json.dumps(card)
            assert "cvv" not in json.dumps(card).lower()

            updated_limits = client.put(
                f"/api/v1/organizations/{org_id}/payment-instruments/"
                f"{instrument_id}/limits",
                json={
                    "single": "250.0000",
                    "daily": "450.0000",
                    "monthly": "1000.0000",
                    "total": "10000.0000",
                },
            )
            assert updated_limits.status_code == 200
            assert updated_limits.json()["limits"]["monthly"] == "1000.0000"

            freeze = client.post(
                f"/api/v1/organizations/{org_id}/payment-instruments/"
                f"{instrument_id}/freeze"
            )
            assert freeze.status_code == 200
            assert freeze.json()["instrument"]["status"] == "freeze_pending"

            invalid = client.post(
                "/api/v1/webhooks/payments/fake",
                headers={
                    "X-Payment-Timestamp": "0",
                    "X-Payment-Signature": "invalid",
                    "Content-Type": "application/json",
                },
                content=b"{}",
            )
            assert invalid.status_code == 400

            freeze_headers, freeze_body = _signed_webhook(
                webhook_secret,
                {
                    "event_id": "evt-freeze-notion",
                    "type": "instrument.frozen",
                    "external_id": external_id,
                },
            )
            first_freeze_event = client.post(
                "/api/v1/webhooks/payments/fake",
                headers=freeze_headers,
                content=freeze_body,
            )
            replay_freeze_event = client.post(
                "/api/v1/webhooks/payments/fake",
                headers=freeze_headers,
                content=freeze_body,
            )
            assert first_freeze_event.status_code == 200
            assert replay_freeze_event.status_code == 200
            assert replay_freeze_event.json()["duplicate"] is True

            unfreeze = client.post(
                f"/api/v1/organizations/{org_id}/payment-instruments/"
                f"{instrument_id}/unfreeze"
            )
            assert unfreeze.status_code == 200
            assert unfreeze.json()["instrument"]["status"] == "unfreeze_pending"

            active_headers, active_body = _signed_webhook(
                webhook_secret,
                {
                    "event_id": "evt-active-notion",
                    "type": "instrument.active",
                    "external_id": external_id,
                },
            )
            active_event = client.post(
                "/api/v1/webhooks/payments/fake",
                headers=active_headers,
                content=active_body,
            )
            assert active_event.status_code == 200

            close = client.post(
                f"/api/v1/organizations/{org_id}/payment-instruments/"
                f"{instrument_id}/close"
            )
            assert close.status_code == 200
            assert close.json()["instrument"]["status"] == "close_pending"

            closed_headers, closed_body = _signed_webhook(
                webhook_secret,
                {
                    "event_id": "evt-closed-notion",
                    "type": "instrument.closed",
                    "external_id": external_id,
                },
            )
            closed_event = client.post(
                "/api/v1/webhooks/payments/fake",
                headers=closed_headers,
                content=closed_body,
            )
            assert closed_event.status_code == 200

            closed_limit_update = client.put(
                f"/api/v1/organizations/{org_id}/payment-instruments/"
                f"{instrument_id}/limits",
                json={
                    "single": "200.0000",
                    "daily": "400.0000",
                    "monthly": "800.0000",
                    "total": "8000.0000",
                },
            )
            assert closed_limit_update.status_code == 409

            settlement_headers, settlement_body = _signed_webhook(
                webhook_secret,
                {
                    "event_id": "evt-settlement-notion",
                    "type": "payment.settled",
                    "external_id": external_id,
                    "transaction_id": "provider-txn-notion-001",
                    "transaction_date": "2026-07-10",
                    "merchant_name": "Notion Labs",
                    "description": "NOTION TEAM PLAN",
                    "amount": "120.0000",
                    "currency": "USD",
                },
            )
            first_settlement = client.post(
                "/api/v1/webhooks/payments/fake",
                headers=settlement_headers,
                content=settlement_body,
            )
            replay_settlement = client.post(
                "/api/v1/webhooks/payments/fake",
                headers=settlement_headers,
                content=settlement_body,
            )
            assert first_settlement.status_code == 200
            assert replay_settlement.json()["duplicate"] is True

            listed = client.get(
                f"/api/v1/organizations/{org_id}/payment-instruments"
            )
            assert listed.status_code == 200
            assert listed.json()["items"][0]["instrument"]["status"] == "closed"

            transactions = client.get(
                f"/api/v1/organizations/{org_id}/transactions"
            )
            assert transactions.status_code == 200
            assert len(transactions.json()["items"]) == 1
            assert transactions.json()["items"][0]["external_id"] == (
                "provider-txn-notion-001"
            )

            client.post("/api/v1/auth/logout")
            other_org_id = _register(client, "other@example.com", "Other")
            other_cards = client.get(
                f"/api/v1/organizations/{other_org_id}/payment-instruments"
            )
            assert other_cards.status_code == 200
            assert other_cards.json()["items"] == []
    finally:
        app.dependency_overrides.clear()
