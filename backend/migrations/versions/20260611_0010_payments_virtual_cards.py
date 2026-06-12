"""Create governed payment requests, instruments, limits, actions, and events.

Revision ID: 20260611_0010
Revises: 20260611_0009
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0010"
down_revision: str | None = "20260611_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_request_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["purchase_request_id"],
            ["purchase_requests.id"],
            name="fk_payment_requests_purchase_request_id_purchase_requests",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_requests"),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_payment_requests_org_idempotency",
        ),
        sa.UniqueConstraint("purchase_request_id", name="uq_payment_requests_purchase_request_id"),
    )
    op.create_index(
        "ix_payment_requests_organization_id",
        "payment_requests",
        ["organization_id"],
    )
    op.create_index("ix_payment_requests_status", "payment_requests", ["status"])

    op.create_table(
        "payment_instruments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("payment_request_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=180), nullable=False),
        sa.Column("brand", sa.String(length=40), nullable=False),
        sa.Column("last4", sa.String(length=4), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sandbox", sa.Boolean(), nullable=False),
        sa.Column("owner_name", sa.String(length=120), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=False),
        sa.Column("merchant_lock", sa.String(length=180), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["payment_request_id"],
            ["payment_requests.id"],
            name="fk_payment_instruments_payment_request_id_payment_requests",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_instruments"),
        sa.UniqueConstraint(
            "provider",
            "external_id",
            name="uq_payment_instruments_provider_external",
        ),
        sa.UniqueConstraint("payment_request_id", name="uq_payment_instruments_payment_request_id"),
    )
    op.create_index(
        "ix_payment_instruments_organization_id",
        "payment_instruments",
        ["organization_id"],
    )
    op.create_index("ix_payment_instruments_status", "payment_instruments", ["status"])

    op.create_table(
        "payment_limits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("single_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("daily_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("total_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["payment_instruments.id"],
            name="fk_payment_limits_instrument_id_payment_instruments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_limits"),
        sa.UniqueConstraint("instrument_id", name="uq_payment_limits_instrument_id"),
    )
    op.create_index(
        "ix_payment_limits_organization_id",
        "payment_limits",
        ["organization_id"],
    )

    op.create_table(
        "payment_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["payment_instruments.id"],
            name="fk_payment_actions_instrument_id_payment_instruments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_actions"),
    )
    op.create_index(
        "ix_payment_actions_organization_id",
        "payment_actions",
        ["organization_id"],
    )
    op.create_index(
        "ix_payment_actions_instrument_id",
        "payment_actions",
        ["instrument_id"],
    )
    op.create_index("ix_payment_actions_action", "payment_actions", ["action"])
    op.create_index("ix_payment_actions_status", "payment_actions", ["status"])

    op.create_table(
        "payment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("event_id", sa.String(length=180), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["payment_instruments.id"],
            name="fk_payment_events_instrument_id_payment_instruments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_events"),
        sa.UniqueConstraint(
            "provider",
            "event_id",
            name="uq_payment_events_provider_event",
        ),
    )
    op.create_index(
        "ix_payment_events_organization_id",
        "payment_events",
        ["organization_id"],
    )
    op.create_index("ix_payment_events_event_type", "payment_events", ["event_type"])
    op.create_index(
        "ix_payment_events_instrument_id",
        "payment_events",
        ["instrument_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_events_instrument_id", table_name="payment_events")
    op.drop_index("ix_payment_events_event_type", table_name="payment_events")
    op.drop_index("ix_payment_events_organization_id", table_name="payment_events")
    op.drop_table("payment_events")
    op.drop_index("ix_payment_actions_status", table_name="payment_actions")
    op.drop_index("ix_payment_actions_action", table_name="payment_actions")
    op.drop_index("ix_payment_actions_instrument_id", table_name="payment_actions")
    op.drop_index("ix_payment_actions_organization_id", table_name="payment_actions")
    op.drop_table("payment_actions")
    op.drop_index("ix_payment_limits_organization_id", table_name="payment_limits")
    op.drop_table("payment_limits")
    op.drop_index("ix_payment_instruments_status", table_name="payment_instruments")
    op.drop_index("ix_payment_instruments_organization_id", table_name="payment_instruments")
    op.drop_table("payment_instruments")
    op.drop_index("ix_payment_requests_status", table_name="payment_requests")
    op.drop_index("ix_payment_requests_organization_id", table_name="payment_requests")
    op.drop_table("payment_requests")
