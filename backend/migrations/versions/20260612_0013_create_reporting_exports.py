"""create reporting exports

Revision ID: 20260612_0013
Revises: 20260612_0012
Create Date: 2026-06-12 13:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_0013"
down_revision: str | None = "20260612_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("query_json", sa.JSON(), nullable=False),
        sa.Column("chart_type", sa.String(length=40), nullable=False),
        sa.Column("visibility", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_saved_reports")),
    )
    op.create_index(op.f("ix_saved_reports_created_by_user_id"), "saved_reports", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_saved_reports_organization_id"), "saved_reports", ["organization_id"], unique=False)
    op.create_index(op.f("ix_saved_reports_visibility"), "saved_reports", ["visibility"], unique=False)
    op.create_table(
        "report_shares",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("saved_report_id", sa.Uuid(), nullable=False),
        sa.Column("share_type", sa.String(length=40), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=True),
        sa.Column("member_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["saved_report_id"],
            ["saved_reports.id"],
            name=op.f("fk_report_shares_saved_report_id_saved_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_shares")),
    )
    op.create_index(op.f("ix_report_shares_member_user_id"), "report_shares", ["member_user_id"], unique=False)
    op.create_index(op.f("ix_report_shares_organization_id"), "report_shares", ["organization_id"], unique=False)
    op.create_index(op.f("ix_report_shares_role"), "report_shares", ["role"], unique=False)
    op.create_index(op.f("ix_report_shares_saved_report_id"), "report_shares", ["saved_report_id"], unique=False)
    op.create_index(op.f("ix_report_shares_share_type"), "report_shares", ["share_type"], unique=False)
    op.create_table(
        "report_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("saved_report_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["saved_report_id"],
            ["saved_reports.id"],
            name=op.f("fk_report_snapshots_saved_report_id_saved_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_snapshots")),
    )
    op.create_index(op.f("ix_report_snapshots_created_by_user_id"), "report_snapshots", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_report_snapshots_organization_id"), "report_snapshots", ["organization_id"], unique=False)
    op.create_index(op.f("ix_report_snapshots_saved_report_id"), "report_snapshots", ["saved_report_id"], unique=False)
    op.create_table(
        "report_exports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("saved_report_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("content_base64", sa.Text(), nullable=False),
        sa.Column("download_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("permissions_snapshot_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["saved_report_id"],
            ["saved_reports.id"],
            name=op.f("fk_report_exports_saved_report_id_saved_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_exports")),
        sa.UniqueConstraint("download_token_hash", name=op.f("uq_report_exports_download_token_hash")),
    )
    op.create_index(op.f("ix_report_exports_created_by_user_id"), "report_exports", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_report_exports_expires_at"), "report_exports", ["expires_at"], unique=False)
    op.create_index(op.f("ix_report_exports_job_id"), "report_exports", ["job_id"], unique=False)
    op.create_index(op.f("ix_report_exports_organization_id"), "report_exports", ["organization_id"], unique=False)
    op.create_index(op.f("ix_report_exports_saved_report_id"), "report_exports", ["saved_report_id"], unique=False)
    op.create_index(op.f("ix_report_exports_status"), "report_exports", ["status"], unique=False)
    op.create_table(
        "report_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("saved_report_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("cron", sa.String(length=80), nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("recipients_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["saved_report_id"],
            ["saved_reports.id"],
            name=op.f("fk_report_subscriptions_saved_report_id_saved_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_subscriptions")),
    )
    op.create_index(op.f("ix_report_subscriptions_created_by_user_id"), "report_subscriptions", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_report_subscriptions_frequency"), "report_subscriptions", ["frequency"], unique=False)
    op.create_index(op.f("ix_report_subscriptions_next_run_at"), "report_subscriptions", ["next_run_at"], unique=False)
    op.create_index(op.f("ix_report_subscriptions_organization_id"), "report_subscriptions", ["organization_id"], unique=False)
    op.create_index(op.f("ix_report_subscriptions_saved_report_id"), "report_subscriptions", ["saved_report_id"], unique=False)
    op.create_index(op.f("ix_report_subscriptions_status"), "report_subscriptions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_subscriptions_status"), table_name="report_subscriptions")
    op.drop_index(op.f("ix_report_subscriptions_saved_report_id"), table_name="report_subscriptions")
    op.drop_index(op.f("ix_report_subscriptions_organization_id"), table_name="report_subscriptions")
    op.drop_index(op.f("ix_report_subscriptions_next_run_at"), table_name="report_subscriptions")
    op.drop_index(op.f("ix_report_subscriptions_frequency"), table_name="report_subscriptions")
    op.drop_index(op.f("ix_report_subscriptions_created_by_user_id"), table_name="report_subscriptions")
    op.drop_table("report_subscriptions")
    op.drop_index(op.f("ix_report_exports_status"), table_name="report_exports")
    op.drop_index(op.f("ix_report_exports_saved_report_id"), table_name="report_exports")
    op.drop_index(op.f("ix_report_exports_organization_id"), table_name="report_exports")
    op.drop_index(op.f("ix_report_exports_job_id"), table_name="report_exports")
    op.drop_index(op.f("ix_report_exports_expires_at"), table_name="report_exports")
    op.drop_index(op.f("ix_report_exports_created_by_user_id"), table_name="report_exports")
    op.drop_table("report_exports")
    op.drop_index(op.f("ix_report_snapshots_saved_report_id"), table_name="report_snapshots")
    op.drop_index(op.f("ix_report_snapshots_organization_id"), table_name="report_snapshots")
    op.drop_index(op.f("ix_report_snapshots_created_by_user_id"), table_name="report_snapshots")
    op.drop_table("report_snapshots")
    op.drop_index(op.f("ix_report_shares_share_type"), table_name="report_shares")
    op.drop_index(op.f("ix_report_shares_saved_report_id"), table_name="report_shares")
    op.drop_index(op.f("ix_report_shares_role"), table_name="report_shares")
    op.drop_index(op.f("ix_report_shares_organization_id"), table_name="report_shares")
    op.drop_index(op.f("ix_report_shares_member_user_id"), table_name="report_shares")
    op.drop_table("report_shares")
    op.drop_index(op.f("ix_saved_reports_visibility"), table_name="saved_reports")
    op.drop_index(op.f("ix_saved_reports_organization_id"), table_name="saved_reports")
    op.drop_index(op.f("ix_saved_reports_created_by_user_id"), table_name="saved_reports")
    op.drop_table("saved_reports")
