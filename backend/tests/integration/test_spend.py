from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.core.money import Money
from app.main import app


def _register(client: TestClient, email: str, organization: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "财务负责人",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    return response.json()["organizations"][0]["id"]


def test_money_uses_decimal_precision() -> None:
    money = Money(amount=Decimal("0.10") + Decimal("0.20"), currency="USD")
    assert money.amount == Decimal("0.30")


def test_budget_transaction_import_split_anomaly_and_period_lock(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'spend.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id = _register(client, "finance@example.com", "Acme 中国")
            budget = client.post(
                f"/api/v1/organizations/{org_id}/budgets",
                json={
                    "name": "2026 IT 软件预算",
                    "fiscal_year": 2026,
                    "department": "IT",
                    "amount": "10000.0000",
                    "currency": "USD",
                },
            )
            assert budget.status_code == 201
            budget_id = budget.json()["id"]

            for commitment_type, amount in [
                ("committed", "1800.0000"),
                ("forecast", "900.0000"),
            ]:
                commitment = client.post(
                    f"/api/v1/organizations/{org_id}/budgets/{budget_id}/commitments",
                    json={
                        "commitment_type": commitment_type,
                        "amount": amount,
                        "description": f"{commitment_type} software",
                    },
                )
                assert commitment.status_code == 201

            first_import = client.post(
                f"/api/v1/organizations/{org_id}/transactions/import",
                json={
                    "source_provider": "stripe",
                    "source_account_id": "card-1",
                    "rows": [
                        {
                            "external_id": "txn-001",
                            "transaction_date": "2026-06-10",
                            "merchant_name": "Notion Labs",
                            "description": "NOTION TEAM",
                            "amount": "4200.0000",
                            "currency": "USD",
                            "department": "IT",
                        }
                    ],
                },
            )
            assert first_import.status_code == 201
            assert first_import.json()["created_count"] == 1
            transaction = first_import.json()["items"][0]
            transaction_id = transaction["id"]
            assert transaction["amount"] == "4200.0000"
            assert transaction["application_id"] is None
            assert transaction["match_confidence"] == "0.0000"

            duplicate_import = client.post(
                f"/api/v1/organizations/{org_id}/transactions/import",
                json={
                    "source_provider": "stripe",
                    "source_account_id": "card-1",
                    "rows": [
                        {
                            "external_id": "txn-001",
                            "transaction_date": "2026-06-10",
                            "merchant_name": "Notion Labs",
                            "description": "NOTION TEAM",
                            "amount": "4200.0000",
                            "currency": "USD",
                            "department": "IT",
                        }
                    ],
                },
            )
            assert duplicate_import.status_code == 201
            assert duplicate_import.json()["created_count"] == 0
            assert duplicate_import.json()["existing_count"] == 1

            summary = client.get(
                f"/api/v1/organizations/{org_id}/budgets/{budget_id}/summary"
            )
            assert summary.status_code == 200
            assert summary.json() == {
                "budget_id": budget_id,
                "currency": "USD",
                "allocated": "10000.0000",
                "actual": "4200.0000",
                "committed": "1800.0000",
                "forecast": "900.0000",
                "remaining": "3100.0000",
            }

            unbalanced = client.post(
                f"/api/v1/organizations/{org_id}/transactions/{transaction_id}/splits",
                json={
                    "splits": [
                        {"amount": "2000.0000", "department": "IT", "category": "协作"},
                        {"amount": "2100.0000", "department": "设计", "category": "协作"},
                    ]
                },
            )
            assert unbalanced.status_code == 422

            balanced = client.post(
                f"/api/v1/organizations/{org_id}/transactions/{transaction_id}/splits",
                json={
                    "splits": [
                        {"amount": "2000.0000", "department": "IT", "category": "协作"},
                        {"amount": "2200.0000", "department": "设计", "category": "协作"},
                    ]
                },
            )
            assert balanced.status_code == 200
            assert len(balanced.json()["splits"]) == 2

            split_summary = client.get(
                f"/api/v1/organizations/{org_id}/budgets/{budget_id}/summary"
            )
            assert split_summary.status_code == 200
            assert split_summary.json()["actual"] == "2000.0000"
            assert split_summary.json()["remaining"] == "5300.0000"

            classified = client.patch(
                f"/api/v1/organizations/{org_id}/transactions/{transaction_id}",
                json={"category": "software", "department": "IT"},
            )
            assert classified.status_code == 200

            over_budget = client.post(
                f"/api/v1/organizations/{org_id}/transactions/import",
                json={
                    "source_provider": "stripe",
                    "source_account_id": "card-1",
                    "rows": [
                        {
                            "external_id": "txn-002",
                            "transaction_date": "2026-07-01",
                            "merchant_name": "Adobe",
                            "description": "ADOBE CREATIVE CLOUD",
                            "amount": "9000.0000",
                            "currency": "USD",
                            "department": "IT",
                        }
                    ],
                },
            )
            assert over_budget.status_code == 201
            over_budget_transaction_id = over_budget.json()["items"][0]["id"]
            anomalies = client.get(
                f"/api/v1/organizations/{org_id}/transaction-anomalies"
            )
            assert anomalies.status_code == 200
            assert anomalies.json()["items"][0]["code"] == "budget_exceeded"
            assert anomalies.json()["items"][0]["rule_version"] == "spend-anomaly-v1"
            assert anomalies.json()["items"][0]["observed_amount"] == "11000.0000"

            reduce_budget_actual = client.post(
                f"/api/v1/organizations/{org_id}/transactions/"
                f"{over_budget_transaction_id}/splits",
                json={
                    "splits": [
                        {"amount": "4000.0000", "department": "IT", "category": "设计"},
                        {"amount": "5000.0000", "department": "设计", "category": "设计"},
                    ]
                },
            )
            assert reduce_budget_actual.status_code == 200
            resolved_anomalies = client.get(
                f"/api/v1/organizations/{org_id}/transaction-anomalies"
            )
            assert resolved_anomalies.status_code == 200
            assert resolved_anomalies.json()["items"][0]["status"] == "resolved"

            period = client.post(
                f"/api/v1/organizations/{org_id}/accounting-periods",
                json={
                    "name": "2026-06",
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-30",
                },
            )
            assert period.status_code == 201
            period_id = period.json()["id"]
            locked = client.post(
                f"/api/v1/organizations/{org_id}/accounting-periods/{period_id}/lock"
            )
            assert locked.status_code == 200
            assert locked.json()["status"] == "locked"

            listed_periods = client.get(
                f"/api/v1/organizations/{org_id}/accounting-periods"
            )
            assert listed_periods.status_code == 200
            assert listed_periods.json()["items"][0]["id"] == period_id
            assert listed_periods.json()["items"][0]["status"] == "locked"

            blocked = client.patch(
                f"/api/v1/organizations/{org_id}/transactions/{transaction_id}",
                json={"category": "collaboration"},
            )
            assert blocked.status_code == 409

            client.post("/api/v1/auth/logout")
            other_org_id = _register(client, "other@example.com", "Other")
            tenant_transactions = client.get(
                f"/api/v1/organizations/{other_org_id}/transactions"
            )
            assert tenant_transactions.status_code == 200
            assert tenant_transactions.json()["items"] == []
            tenant_periods = client.get(
                f"/api/v1/organizations/{other_org_id}/accounting-periods"
            )
            assert tenant_periods.status_code == 200
            assert tenant_periods.json()["items"] == []
    finally:
        app.dependency_overrides.clear()
