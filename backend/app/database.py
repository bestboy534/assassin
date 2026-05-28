import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import HistoryRun, SubscriptionItem


def _connect(sqlite_path: str) -> sqlite3.Connection:
    db_path = Path(sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(sqlite_path: str) -> None:
    with _connect(sqlite_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                source_hint TEXT NOT NULL,
                items_count INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subscription_items (
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
                risk_note TEXT,
                PRIMARY KEY (run_id, item_id),
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
            );
            """
        )


def save_analysis_run(sqlite_path: str, source_hint: str, items: list[SubscriptionItem]) -> str:
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect(sqlite_path) as conn:
        conn.execute(
            "INSERT INTO analysis_runs (id, created_at, source_hint, items_count) VALUES (?, ?, ?, ?)",
            (run_id, created_at, source_hint, len(items)),
        )
        for item in items:
            conn.execute(
                """
                INSERT INTO subscription_items (
                    run_id, item_id, software_name, merchant_name, amount, currency, billing_cycle,
                    transaction_date, normalized_amount_usd, monthly_cost_usd, status, risk_type,
                    confidence, evidence, needs_user_confirmation, cancel_url, fallback_search_url,
                    support_email, guide_steps_json, risk_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    item.id,
                    item.software_name,
                    item.merchant_name,
                    item.amount,
                    item.currency,
                    item.billing_cycle,
                    item.transaction_date,
                    item.normalized_amount_usd,
                    item.monthly_cost_usd,
                    item.status,
                    item.risk_type,
                    item.confidence,
                    item.evidence,
                    1 if item.needs_user_confirmation else 0,
                    item.cancel_url,
                    item.fallback_search_url,
                    item.support_email,
                    json.dumps(item.guide_steps, ensure_ascii=False),
                    item.risk_note,
                ),
            )
    return run_id


def list_history_runs(sqlite_path: str, limit: int = 20) -> list[HistoryRun]:
    with _connect(sqlite_path) as conn:
        rows = conn.execute(
            "SELECT id, created_at, source_hint, items_count FROM analysis_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [HistoryRun(**dict(row)) for row in rows]


def get_history_run(sqlite_path: str, run_id: str) -> tuple[HistoryRun, list[SubscriptionItem]] | None:
    with _connect(sqlite_path) as conn:
        run_row = conn.execute(
            "SELECT id, created_at, source_hint, items_count FROM analysis_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if not run_row:
            return None
        item_rows = conn.execute(
            "SELECT * FROM subscription_items WHERE run_id = ? ORDER BY rowid ASC",
            (run_id,),
        ).fetchall()

    items: list[SubscriptionItem] = []
    for row in item_rows:
        data: dict[str, Any] = dict(row)
        items.append(
            SubscriptionItem(
                id=data["item_id"],
                software_name=data["software_name"],
                merchant_name=data["merchant_name"],
                amount=data["amount"],
                currency=data["currency"],
                billing_cycle=data["billing_cycle"],
                transaction_date=data["transaction_date"],
                normalized_amount_usd=data["normalized_amount_usd"],
                monthly_cost_usd=data["monthly_cost_usd"],
                status=data["status"],
                risk_type=data["risk_type"],
                confidence=data["confidence"],
                evidence=data["evidence"],
                needs_user_confirmation=bool(data["needs_user_confirmation"]),
                cancel_url=data["cancel_url"],
                fallback_search_url=data["fallback_search_url"],
                support_email=data["support_email"],
                guide_steps=json.loads(data["guide_steps_json"] or "[]"),
                risk_note=data["risk_note"],
            )
        )
    return HistoryRun(**dict(run_row)), items
