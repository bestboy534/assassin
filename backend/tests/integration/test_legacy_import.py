import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.cli import migrate_sqlite_analysis
from app.core.database import Database
from app.domains.audit_ai.models import AnalysisItem, AnalysisRun


def create_legacy_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE analysis_runs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                source_hint TEXT NOT NULL,
                items_count INTEGER NOT NULL
            );
            CREATE TABLE subscription_items (
                run_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                software_name TEXT NOT NULL,
                merchant_name TEXT,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                billing_cycle TEXT NOT NULL,
                transaction_date TEXT,
                normalized_amount_usd REAL NOT NULL,
                monthly_cost_usd REAL NOT NULL,
                status TEXT NOT NULL,
                risk_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence TEXT NOT NULL,
                needs_user_confirmation INTEGER NOT NULL,
                cancel_url TEXT,
                fallback_search_url TEXT,
                support_email TEXT,
                guide_steps_json TEXT NOT NULL,
                risk_note TEXT
            );
            INSERT INTO analysis_runs VALUES (
                'run_legacy',
                '2026-06-11T00:00:00+00:00',
                'csv',
                1
            );
            INSERT INTO subscription_items VALUES (
                'run_legacy',
                'sub_legacy',
                'ChatGPT Plus',
                'OPENAI',
                20.0,
                'USD',
                'monthly',
                '2026-06-01',
                20.0,
                20.0,
                'need_confirm',
                'possible_idle',
                0.9,
                'legacy evidence',
                1,
                NULL,
                NULL,
                NULL,
                '[]',
                NULL
            );
            """
        )


@pytest.mark.asyncio
async def test_legacy_analysis_import_is_idempotent(
    database: Database,
    tmp_path: Path,
) -> None:
    source = tmp_path / "legacy.db"
    create_legacy_database(source)

    assert await migrate_sqlite_analysis(source, database) == 1
    assert await migrate_sqlite_analysis(source, database) == 0

    async with database.session_factory() as session:
        assert await session.get(AnalysisRun, "run_legacy") is not None
        assert await session.scalar(select(func.count(AnalysisItem.item_id))) == 1
