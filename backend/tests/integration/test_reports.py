import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.reports.schemas import DateRange, ReportQuery
from app.domains.reports.service import ReportAccessContext, ReportService
from app.domains.spend.models import SpendTransaction
from app.main import app


def _register(client: TestClient, email: str, organization: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "报表管理员",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


async def _seed_spend(database: Database, organization_id: str) -> None:
    organization_uuid = UUID(organization_id)
    async with database.session_factory() as session:
        session.add_all(
            [
                SpendTransaction(
                    organization_id=organization_uuid,
                    source_provider="csv",
                    source_account_id="card",
                    external_id="txn-it",
                    transaction_date=date(2026, 6, 1),
                    merchant_name="Notion Labs",
                    description="Notion enterprise",
                    amount=Decimal("100.00"),
                    currency="USD",
                    department="IT",
                    category="collaboration",
                    match_confidence=Decimal("0.9500"),
                ),
                SpendTransaction(
                    organization_id=organization_uuid,
                    source_provider="csv",
                    source_account_id="card",
                    external_id="txn-design",
                    transaction_date=date(2026, 6, 2),
                    merchant_name="Figma",
                    description="Figma seats",
                    amount=Decimal("300.00"),
                    currency="USD",
                    department="Design",
                    category="design",
                    match_confidence=Decimal("0.9000"),
                ),
            ]
        )
        await session.commit()


async def _add_source_mutation(database: Database, organization_id: str) -> None:
    organization_uuid = UUID(organization_id)
    async with database.session_factory() as session:
        session.add(
            SpendTransaction(
                organization_id=organization_uuid,
                source_provider="csv",
                source_account_id="card",
                external_id="txn-it-later",
                transaction_date=date(2026, 6, 3),
                merchant_name="Slack",
                description="Slack seats",
                amount=Decimal("50.00"),
                currency="USD",
                department="IT",
                category="collaboration",
                match_confidence=Decimal("0.8800"),
            )
        )
        await session.commit()


def test_department_scoped_user_only_sees_department_spend(database: Database) -> None:
    async def run() -> None:
        organization_id = "00000000-0000-0000-0000-000000000001"
        user_id = "00000000-0000-0000-0000-000000000002"
        await _seed_spend(database, organization_id)
        async with database.session_factory() as session:
            result = await ReportService(session).query(
                ReportAccessContext(
                    organization_id=organization_id,
                    user_id=user_id,
                    role="member",
                    allowed_departments=frozenset({"IT"}),
                ),
                ReportQuery(
                    metrics=["monthly_spend"],
                    date_range=DateRange(start=date(2026, 6, 1), end=date(2026, 6, 30)),
                    group_by=["department"],
                ),
            )

        assert [row.dimensions["department"] for row in result.rows] == ["IT"]
        assert result.rows[0].metrics["monthly_spend"] == Decimal("100.0000")

    asyncio.run(run())


def test_reports_query_snapshot_export_and_subscription(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'reports.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id, _ = _register(client, "reports@example.com", "报表验证")
            asyncio.run(_seed_spend(database, org_id))

            query = {
                "metrics": ["monthly_spend"],
                "date_range": {"start": "2026-06-01", "end": "2026-06-30"},
                "group_by": ["department"],
                "filters": [],
            }
            queried = client.post(
                f"/api/v1/organizations/{org_id}/reports/query",
                json=query,
            )
            assert queried.status_code == 200
            rows = queried.json()["rows"]
            assert {row["dimensions"]["department"] for row in rows} == {"IT", "Design"}

            saved = client.post(
                f"/api/v1/organizations/{org_id}/reports/saved-reports",
                json={
                    "name": "部门支出报表",
                    "description": "按部门查看月度软件支出",
                    "query": query,
                    "chart_type": "bar",
                    "visibility": "organization",
                },
            )
            assert saved.status_code == 201
            report_id = saved.json()["id"]

            snapshot = client.post(
                f"/api/v1/organizations/{org_id}/reports/saved-reports/"
                f"{report_id}/snapshots"
            )
            assert snapshot.status_code == 201
            snapshot_payload = snapshot.json()["payload"]
            assert snapshot_payload["rows"][0]["metrics"]["monthly_spend"]

            asyncio.run(_add_source_mutation(database, org_id))
            fetched_snapshot = client.get(
                f"/api/v1/organizations/{org_id}/reports/saved-reports/"
                f"{report_id}/snapshots/{snapshot.json()['id']}"
            )
            assert fetched_snapshot.status_code == 200
            assert fetched_snapshot.json()["payload"] == snapshot_payload

            export = client.post(
                f"/api/v1/organizations/{org_id}/reports/saved-reports/"
                f"{report_id}/exports",
                json={"format": "xlsx"},
            )
            assert export.status_code == 201
            export_payload = export.json()
            assert export_payload["status"] == "succeeded"
            assert export_payload["row_count"] == 2
            assert export_payload["download_url"]
            assert "full_card_number" not in export.text

            downloaded = client.get(export_payload["download_url"])
            assert downloaded.status_code == 200
            assert downloaded.headers["content-disposition"].endswith(".xlsx\"")
            assert downloaded.content.startswith(b"PK")

            subscription = client.post(
                f"/api/v1/organizations/{org_id}/reports/saved-reports/"
                f"{report_id}/subscriptions",
                json={
                    "frequency": "monthly",
                    "cron": "0 9 1 * *",
                    "timezone": "Asia/Hong_Kong",
                    "recipients": ["finance@example.com"],
                },
            )
            assert subscription.status_code == 201
            next_run = datetime.fromisoformat(subscription.json()["next_run_at"])
            assert next_run.tzinfo == UTC
            assert next_run.hour == 1
    finally:
        app.dependency_overrides.clear()
