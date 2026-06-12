import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config


def test_migrations_upgrade_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite+aiosqlite:///{database_path}",
    )
    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert {
        "jobs",
        "outbox_events",
        "inbox_receipts",
        "files",
        "savings_opportunities",
        "optimization_projects",
        "payment_requests",
        "payment_instruments",
        "payment_events",
        "invoices",
        "invoice_versions",
        "invoice_matches",
        "accounting_mappings",
        "accounting_exports",
        "accounting_sync_records",
        "integration_connections",
        "integration_credentials",
        "integration_definitions",
        "integration_field_mappings",
        "integration_oauth_states",
        "sync_cursors",
        "sync_errors",
        "sync_runs",
        "saved_reports",
        "report_shares",
        "report_snapshots",
        "report_exports",
        "report_subscriptions",
        "audit_logs",
        "retention_policies",
        "legal_holds",
        "deletion_jobs",
        "deletion_job_items",
        "privacy_requests",
        "privacy_request_actions",
        "compliance_frameworks",
        "compliance_controls",
        "control_owners",
        "control_evidence",
        "control_reviews",
        "security_incidents",
        "incident_tasks",
    } <= tables
    assert version == ("20260612_0017",)
