"""create API keys and outbound webhooks

Revision ID: 20260612_0018
Revises: 20260612_0017
Create Date: 2026-06-12 19:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_0018"
down_revision: str | None = "20260612_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("prefix", sa.String(length=24), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_keys")),
        sa.UniqueConstraint("prefix", name=op.f("uq_api_keys_prefix")),
        sa.UniqueConstraint("secret_hash", name=op.f("uq_api_keys_secret_hash")),
    )
    for column in (
        "organization_id",
        "created_by_user_id",
        "prefix",
        "expires_at",
        "revoked_at",
    ):
        op.create_index(op.f(f"ix_api_keys_{column}"), "api_keys", [column], unique=False)

    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("events_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("secret_version", sa.Integer(), nullable=False),
        sa.Column("secret_cipher_suite", sa.String(length=80), nullable=False),
        sa.Column("secret_ciphertext", sa.Text(), nullable=False),
        sa.Column("previous_secret_version", sa.Integer(), nullable=True),
        sa.Column("previous_secret_cipher_suite", sa.String(length=80), nullable=True),
        sa.Column("previous_secret_ciphertext", sa.Text(), nullable=True),
        sa.Column("previous_secret_expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_endpoints")),
    )
    for column in ("organization_id", "created_by_user_id", "status"):
        op.create_index(
            op.f(f"ix_webhook_endpoints_{column}"),
            "webhook_endpoints",
            [column],
            unique=False,
        )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=160), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("secret_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.String(length=500), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
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
            ["endpoint_id"],
            ["webhook_endpoints.id"],
            name=op.f("fk_webhook_deliveries_endpoint_id_webhook_endpoints"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_deliveries")),
        sa.UniqueConstraint(
            "endpoint_id",
            "event_id",
            name="uq_webhook_delivery_endpoint_event",
        ),
    )
    for column in (
        "organization_id",
        "endpoint_id",
        "event_id",
        "event_type",
        "status",
        "next_attempt_at",
    ):
        op.create_index(
            op.f(f"ix_webhook_deliveries_{column}"),
            "webhook_deliveries",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in (
        "next_attempt_at",
        "status",
        "event_type",
        "event_id",
        "endpoint_id",
        "organization_id",
    ):
        op.drop_index(
            op.f(f"ix_webhook_deliveries_{column}"),
            table_name="webhook_deliveries",
        )
    op.drop_table("webhook_deliveries")

    for column in ("status", "created_by_user_id", "organization_id"):
        op.drop_index(
            op.f(f"ix_webhook_endpoints_{column}"),
            table_name="webhook_endpoints",
        )
    op.drop_table("webhook_endpoints")

    for column in (
        "revoked_at",
        "expires_at",
        "prefix",
        "created_by_user_id",
        "organization_id",
    ):
        op.drop_index(op.f(f"ix_api_keys_{column}"), table_name="api_keys")
    op.drop_table("api_keys")
