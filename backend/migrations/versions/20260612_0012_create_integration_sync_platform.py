"""create integration sync platform

Revision ID: 20260612_0012
Revises: 20260611_0011
Create Date: 2026-06-12 10:18:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_0012"
down_revision: str | None = "20260611_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("auth_type", sa.String(length=40), nullable=False),
        sa.Column("capabilities_json", sa.Text(), nullable=False),
        sa.Column("resource_types_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_integration_definitions")),
        sa.UniqueConstraint("key", name=op.f("uq_integration_definitions_key")),
    )
    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("auth_type", sa.String(length=40), nullable=False),
        sa.Column("credential_label", sa.String(length=120), nullable=False),
        sa.Column("credential_last4", sa.String(length=8), nullable=False),
        sa.Column("sandbox_options_json", sa.Text(), nullable=False),
        sa.Column("last_health_status", sa.String(length=40), nullable=True),
        sa.Column("last_health_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
            ["definition_id"],
            ["integration_definitions.id"],
            name=op.f("fk_integration_connections_definition_id_integration_definitions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_integration_connections")),
    )
    op.create_index(
        op.f("ix_integration_connections_definition_id"),
        "integration_connections",
        ["definition_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_integration_connections_organization_id"),
        "integration_connections",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_integration_connections_status"),
        "integration_connections",
        ["status"],
        unique=False,
    )
    op.create_table(
        "integration_oauth_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("definition_key", sa.String(length=80), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("pkce_verifier_hash", sa.String(length=64), nullable=False),
        sa.Column("redirect_uri", sa.String(length=500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_integration_oauth_states")),
        sa.UniqueConstraint("state_hash", name=op.f("uq_integration_oauth_states_state_hash")),
    )
    op.create_index(
        op.f("ix_integration_oauth_states_organization_id"),
        "integration_oauth_states",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "integration_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("cipher_suite", sa.String(length=80), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["integration_connections.id"],
            name=op.f("fk_integration_credentials_connection_id_integration_connections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_integration_credentials")),
        sa.UniqueConstraint("connection_id", name=op.f("uq_integration_credentials_connection_id")),
    )
    op.create_index(
        op.f("ix_integration_credentials_organization_id"),
        "integration_credentials",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "integration_field_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("source_field", sa.String(length=120), nullable=False),
        sa.Column("target_field", sa.String(length=120), nullable=False),
        sa.Column("transform", sa.String(length=80), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["integration_connections.id"],
            name=op.f("fk_integration_field_mappings_connection_id_integration_connections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_integration_field_mappings")),
        sa.UniqueConstraint(
            "organization_id",
            "connection_id",
            "resource_type",
            "source_field",
            name="uq_integration_field_mapping",
        ),
    )
    op.create_index(
        op.f("ix_integration_field_mappings_connection_id"),
        "integration_field_mappings",
        ["connection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_integration_field_mappings_organization_id"),
        "integration_field_mappings",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("cursor_before", sa.String(length=180), nullable=True),
        sa.Column("cursor_after", sa.String(length=180), nullable=True),
        sa.Column("read_count", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.String(length=500), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["integration_connections.id"],
            name=op.f("fk_sync_runs_connection_id_integration_connections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_runs")),
    )
    op.create_index(op.f("ix_sync_runs_connection_id"), "sync_runs", ["connection_id"], unique=False)
    op.create_index(op.f("ix_sync_runs_organization_id"), "sync_runs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_sync_runs_status"), "sync_runs", ["status"], unique=False)
    op.create_table(
        "sync_cursors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("cursor", sa.String(length=180), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["integration_connections.id"],
            name=op.f("fk_sync_cursors_connection_id_integration_connections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_cursors")),
        sa.UniqueConstraint(
            "organization_id",
            "connection_id",
            "resource_type",
            name="uq_sync_cursor_scope",
        ),
    )
    op.create_index(op.f("ix_sync_cursors_connection_id"), "sync_cursors", ["connection_id"], unique=False)
    op.create_index(op.f("ix_sync_cursors_organization_id"), "sync_cursors", ["organization_id"], unique=False)
    op.create_table(
        "sync_errors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("sync_run_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("external_id", sa.String(length=180), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["integration_connections.id"],
            name=op.f("fk_sync_errors_connection_id_integration_connections"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sync_run_id"],
            ["sync_runs.id"],
            name=op.f("fk_sync_errors_sync_run_id_sync_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_errors")),
    )
    op.create_index(op.f("ix_sync_errors_connection_id"), "sync_errors", ["connection_id"], unique=False)
    op.create_index(op.f("ix_sync_errors_organization_id"), "sync_errors", ["organization_id"], unique=False)
    op.create_index(op.f("ix_sync_errors_sync_run_id"), "sync_errors", ["sync_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sync_errors_sync_run_id"), table_name="sync_errors")
    op.drop_index(op.f("ix_sync_errors_organization_id"), table_name="sync_errors")
    op.drop_index(op.f("ix_sync_errors_connection_id"), table_name="sync_errors")
    op.drop_table("sync_errors")
    op.drop_index(op.f("ix_sync_cursors_organization_id"), table_name="sync_cursors")
    op.drop_index(op.f("ix_sync_cursors_connection_id"), table_name="sync_cursors")
    op.drop_table("sync_cursors")
    op.drop_index(op.f("ix_sync_runs_status"), table_name="sync_runs")
    op.drop_index(op.f("ix_sync_runs_organization_id"), table_name="sync_runs")
    op.drop_index(op.f("ix_sync_runs_connection_id"), table_name="sync_runs")
    op.drop_table("sync_runs")
    op.drop_index(op.f("ix_integration_field_mappings_organization_id"), table_name="integration_field_mappings")
    op.drop_index(op.f("ix_integration_field_mappings_connection_id"), table_name="integration_field_mappings")
    op.drop_table("integration_field_mappings")
    op.drop_index(op.f("ix_integration_credentials_organization_id"), table_name="integration_credentials")
    op.drop_table("integration_credentials")
    op.drop_index(op.f("ix_integration_oauth_states_organization_id"), table_name="integration_oauth_states")
    op.drop_table("integration_oauth_states")
    op.drop_index(op.f("ix_integration_connections_status"), table_name="integration_connections")
    op.drop_index(op.f("ix_integration_connections_organization_id"), table_name="integration_connections")
    op.drop_index(op.f("ix_integration_connections_definition_id"), table_name="integration_connections")
    op.drop_table("integration_connections")
    op.drop_table("integration_definitions")
