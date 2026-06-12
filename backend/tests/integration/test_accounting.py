from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.main import app


def _register(client: TestClient, email: str, organization: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "会计负责人",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    session = response.json()
    return session["organizations"][0]["id"], session["user"]["id"]


def test_invoice_review_matching_mapping_export_and_resync(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'accounting.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id, _ = _register(client, "accounting@example.com", "Acme 中国")
            application = client.post(
                f"/api/v1/organizations/{org_id}/applications",
                json={
                    "name": "Notion",
                    "category": "collaboration",
                    "business_owner": "运营",
                    "technical_owner": "IT",
                    "risk_level": "low",
                    "approved": True,
                },
            ).json()
            vendor = client.post(
                f"/api/v1/organizations/{org_id}/vendors",
                json={
                    "name": "Notion Labs",
                    "domain": "notion.so",
                    "country_code": "US",
                    "category": "software",
                    "business_owner": "运营",
                    "risk_owner": "安全",
                },
            ).json()
            contract_bundle = client.post(
                f"/api/v1/organizations/{org_id}/contracts",
                json={
                    "name": "Notion 2026",
                    "vendor_name": "Notion Labs",
                    "application_name": "Notion",
                    "owner_name": "运营负责人",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "amount": 1416,
                    "currency": "USD",
                    "billing_frequency": "monthly",
                    "auto_renew": True,
                    "notice_period_days": 30,
                },
            ).json()
            transactions = client.post(
                f"/api/v1/organizations/{org_id}/transactions/import",
                json={
                    "source_provider": "bank",
                    "source_account_id": "ops-card",
                    "rows": [
                        {
                            "external_id": "txn-notion-2026-07",
                            "transaction_date": "2026-07-10",
                            "merchant_name": "Notion Labs",
                            "description": "NOTION ENTERPRISE",
                            "amount": "118.0000",
                            "currency": "USD",
                            "department": "运营",
                        }
                    ],
                },
            ).json()

            extracted = client.post(
                f"/api/v1/organizations/{org_id}/invoices/extract",
                headers={"Idempotency-Key": "invoice-notion-2026-07"},
                json={
                    "source_type": "manual_text",
                    "external_id": "mail-notion-2026-07",
                    "filename": "notion-july.txt",
                    "text": (
                        "vendor: Notion Labs\n"
                        "invoice_number: INV-2026-001\n"
                        "invoice_date: 2026-07-10\n"
                        "due_date: 2026-08-09\n"
                        "currency: USD\n"
                        "subtotal: 100.00\n"
                        "tax: 15.00\n"
                        "total: 118.00\n"
                        "line: Notion enterprise subscription | 1 | 118.00"
                    ),
                },
            )
            assert extracted.status_code == 201
            invoice = extracted.json()
            invoice_id = invoice["invoice"]["id"]
            assert invoice["invoice"]["status"] == "review_required"
            assert invoice["invoice"]["exception_codes"] == ["amount_imbalance"]
            assert invoice["extraction"]["fields"]["total"]["evidence"]["page"] == 1

            confirmed = client.post(
                f"/api/v1/organizations/{org_id}/invoices/{invoice_id}/confirm",
                json={
                    "vendor_name": "Notion Labs",
                    "invoice_number": "INV-2026-001",
                    "invoice_date": "2026-07-10",
                    "due_date": "2026-08-09",
                    "currency": "USD",
                    "subtotal": "100.0000",
                    "tax": "18.0000",
                    "total": "118.0000",
                    "purchase_order_number": "",
                    "line_items": [
                        {
                            "description": "Notion enterprise subscription",
                            "quantity": "1.0000",
                            "unit_price": "118.0000",
                            "amount": "118.0000",
                            "category": "software",
                        }
                    ],
                },
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["invoice"]["status"] == "ready"

            matched = client.post(
                f"/api/v1/organizations/{org_id}/invoices/{invoice_id}/match"
            )
            assert matched.status_code == 200
            match = matched.json()["match"]
            assert match["vendor_id"] == vendor["id"]
            assert match["contract_id"] == contract_bundle["contract"]["id"]
            assert match["transaction_id"] == transactions["items"][0]["id"]
            assert match["application_id"] == application["id"]
            assert match["confidence"] == "1.0000"

            client.post(
                f"/api/v1/organizations/{org_id}/accounting-mappings",
                json={
                    "scope_type": "default",
                    "scope_value": "*",
                    "account_code": "6000",
                    "tax_code": "VAT18",
                    "cost_center": "GLOBAL",
                    "department": "财务",
                    "project": "",
                },
            )
            client.post(
                f"/api/v1/organizations/{org_id}/accounting-mappings",
                json={
                    "scope_type": "vendor",
                    "scope_value": vendor["id"],
                    "account_code": "6100",
                    "tax_code": "VAT18",
                    "cost_center": "OPS",
                    "department": "运营",
                    "project": "",
                },
            )
            client.post(
                f"/api/v1/organizations/{org_id}/accounting-mappings",
                json={
                    "scope_type": "application",
                    "scope_value": application["id"],
                    "account_code": "6200",
                    "tax_code": "VAT18",
                    "cost_center": "OPS-SAAS",
                    "department": "运营",
                    "project": "数字化",
                },
            )

            resolved = client.get(
                f"/api/v1/organizations/{org_id}/invoices/{invoice_id}/mapping"
            )
            assert resolved.status_code == 200
            assert resolved.json()["account_code"] == "6200"
            assert resolved.json()["resolved_scope_type"] == "application"

            exported = client.post(
                f"/api/v1/organizations/{org_id}/invoices/{invoice_id}/export",
                headers={"Idempotency-Key": "export-notion-2026-07"},
            )
            assert exported.status_code == 200
            export = exported.json()["export"]
            assert export["status"] == "synced"
            assert export["external_id"].startswith("sandbox_bill_")

            changed = client.patch(
                f"/api/v1/organizations/{org_id}/invoices/{invoice_id}",
                json={
                    "subtotal": "102.0000",
                    "tax": "18.0000",
                    "total": "120.0000",
                },
            )
            assert changed.status_code == 200
            assert changed.json()["invoice"]["status"] == "out_of_sync"
            assert changed.json()["export"]["status"] == "out_of_sync"
            assert "total" in changed.json()["export"]["diff"]

            resynced = client.post(
                f"/api/v1/organizations/{org_id}/accounting-exports/{export['id']}/retry"
            )
            assert resynced.status_code == 200
            assert resynced.json()["status"] == "synced"
            assert resynced.json()["external_id"] == export["external_id"]

            duplicate = client.post(
                f"/api/v1/organizations/{org_id}/invoices/extract",
                headers={"Idempotency-Key": "invoice-notion-duplicate"},
                json={
                    "source_type": "api",
                    "external_id": "api-notion-duplicate",
                    "filename": "duplicate.txt",
                    "text": (
                        "vendor: Notion Labs\n"
                        "invoice_number: INV-2026-001\n"
                        "invoice_date: 2026-07-10\n"
                        "due_date: 2026-08-09\n"
                        "currency: USD\n"
                        "subtotal: 100.00\n"
                        "tax: 18.00\n"
                        "total: 118.00"
                    ),
                },
            )
            assert duplicate.status_code == 201
            assert duplicate.json()["invoice"]["status"] == "duplicate"
            assert duplicate.json()["invoice"]["duplicate_of_id"] == invoice_id

            client.post("/api/v1/auth/logout")
            other_org_id, _ = _register(
                client,
                "other-accounting@example.com",
                "Other",
            )
            other_invoices = client.get(
                f"/api/v1/organizations/{other_org_id}/invoices"
            )
            assert other_invoices.status_code == 200
            assert other_invoices.json()["items"] == []
    finally:
        app.dependency_overrides.clear()
