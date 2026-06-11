import argparse
import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.database import Database, get_database
from app.domains.audit_ai.models import AnalysisItem, AnalysisRun


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SaaS Assassin backend maintenance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    migrate = subparsers.add_parser(
        "migrate-sqlite-analysis",
        help="Idempotently import legacy analysis history into DATABASE_URL",
    )
    migrate.add_argument("--source", required=True, type=Path)
    return parser.parse_args()


def read_legacy_rows(source: Path) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    connection = sqlite3.connect(source)
    connection.row_factory = sqlite3.Row
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        run_table = "legacy_analysis_runs" if "legacy_analysis_runs" in tables else "analysis_runs"
        item_table = (
            "legacy_subscription_items"
            if "legacy_subscription_items" in tables
            else "subscription_items"
        )
        runs = connection.execute(
            f"SELECT id, created_at, source_hint, items_count FROM {run_table}"
        ).fetchall()
        result = []
        for run in runs:
            items = connection.execute(
                f"SELECT * FROM {item_table} WHERE run_id = ? ORDER BY rowid",
                (run["id"],),
            ).fetchall()
            result.append((dict(run), [dict(item) for item in items]))
        return result
    finally:
        connection.close()


async def migrate_sqlite_analysis(
    source: Path,
    database: Database | None = None,
) -> int:
    if not source.is_file():
        raise FileNotFoundError(source)
    target = database or get_database()
    owns_database = database is None
    imported = 0
    async with target.session_factory() as session:
        for run_row, item_rows in read_legacy_rows(source):
            exists = await session.scalar(
                select(AnalysisRun.id).where(AnalysisRun.id == run_row["id"])
            )
            if exists is not None:
                continue
            run = AnalysisRun(
                id=run_row["id"],
                created_at=datetime.fromisoformat(run_row["created_at"]),
                source_hint=run_row["source_hint"],
                items_count=run_row["items_count"],
            )
            for position, item in enumerate(item_rows):
                run.items.append(
                    AnalysisItem(
                        item_id=item["item_id"],
                        position=position,
                        software_name=item["software_name"],
                        merchant_name=item["merchant_name"],
                        amount=item["amount"],
                        currency=item["currency"],
                        billing_cycle=item["billing_cycle"],
                        transaction_date=item["transaction_date"],
                        normalized_amount_usd=item["normalized_amount_usd"],
                        monthly_cost_usd=item["monthly_cost_usd"],
                        status=item["status"],
                        risk_type=item["risk_type"],
                        confidence=item["confidence"],
                        evidence=item["evidence"],
                        needs_user_confirmation=bool(item["needs_user_confirmation"]),
                        cancel_url=item["cancel_url"],
                        fallback_search_url=item["fallback_search_url"],
                        support_email=item["support_email"],
                        guide_steps_json=item["guide_steps_json"] or json.dumps([]),
                        risk_note=item["risk_note"],
                    )
                )
            session.add(run)
            imported += 1
        await session.commit()
    if owns_database:
        await target.dispose()
    return imported


async def async_main() -> None:
    args = parse_args()
    if args.command == "migrate-sqlite-analysis":
        imported = await migrate_sqlite_analysis(args.source)
        print(f"Imported {imported} analysis runs")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
