"""create billing plans, entitlements, subscriptions, and usage

Revision ID: 20260613_0019
Revises: 20260612_0018
Create Date: 2026-06-13 11:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0019"
down_revision: str | None = "20260612_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plans")),
        sa.UniqueConstraint("key", name=op.f("uq_plans_key")),
    )
    op.create_index(op.f("ix_plans_key"), "plans", ["key"], unique=False)
    op.create_index(op.f("ix_plans_status"), "plans", ["status"], unique=False)

    op.create_table(
        "plan_prices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("billing_interval", sa.String(length=24), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("external_price_id", sa.String(length=180), nullable=True),
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
            ["plan_id"],
            ["plans.id"],
            name=op.f("fk_plan_prices_plan_id_plans"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_prices")),
        sa.UniqueConstraint(
            "plan_id",
            "currency",
            "billing_interval",
            name="uq_plan_price_currency_interval",
        ),
    )
    for column in ("plan_id", "status", "external_price_id"):
        op.create_index(
            op.f(f"ix_plan_prices_{column}"),
            "plan_prices",
            [column],
            unique=False,
        )

    op.create_table(
        "plan_entitlements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("hard_limit", sa.Boolean(), nullable=False),
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
            ["plan_id"],
            ["plans.id"],
            name=op.f("fk_plan_entitlements_plan_id_plans"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_entitlements")),
        sa.UniqueConstraint("plan_id", "key", name="uq_plan_entitlement_key"),
    )
    for column in ("plan_id", "key", "value_type"):
        op.create_index(
            op.f(f"ix_plan_entitlements_{column}"),
            "plan_entitlements",
            [column],
            unique=False,
        )

    op.create_table(
        "organization_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_subscription_id", sa.String(length=180), nullable=True),
        sa.Column("provider_version", sa.BigInteger(), nullable=False),
        sa.Column("read_only", sa.Boolean(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
            ["organization_id"],
            ["organizations.id"],
            name=op.f(
                "fk_organization_subscriptions_organization_id_organizations"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["plans.id"],
            name=op.f("fk_organization_subscriptions_plan_id_plans"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_subscriptions")),
        sa.UniqueConstraint(
            "organization_id",
            name="uq_organization_subscription",
        ),
    )
    for column in (
        "organization_id",
        "plan_id",
        "status",
        "provider_subscription_id",
        "trial_ends_at",
        "current_period_end",
    ):
        op.create_index(
            op.f(f"ix_organization_subscriptions_{column}"),
            "organization_subscriptions",
            [column],
            unique=False,
        )

    op.create_table(
        "organization_entitlements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
            ["organization_id"],
            ["organizations.id"],
            name=op.f(
                "fk_organization_entitlements_organization_id_organizations"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_entitlements")),
        sa.UniqueConstraint(
            "organization_id",
            "key",
            name="uq_organization_entitlement_key",
        ),
    )
    for column in ("organization_id", "key", "value_type", "expires_at"):
        op.create_index(
            op.f(f"ix_organization_entitlements_{column}"),
            "organization_entitlements",
            [column],
            unique=False,
        )

    op.create_table(
        "usage_counters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("metric", sa.String(length=120), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_value", sa.BigInteger(), nullable=False),
        sa.Column("soft_limit", sa.BigInteger(), nullable=True),
        sa.Column("hard_limit", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
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
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_usage_counters_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_counters")),
        sa.UniqueConstraint(
            "organization_id",
            "metric",
            "period_start",
            name="uq_usage_counter_period",
        ),
    )
    for column in ("organization_id", "metric", "period_end", "status"):
        op.create_index(
            op.f(f"ix_usage_counters_{column}"),
            "usage_counters",
            [column],
            unique=False,
        )

    op.create_table(
        "usage_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("metric", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("source_key", sa.String(length=240), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_usage_events_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_events")),
        sa.UniqueConstraint(
            "organization_id",
            "metric",
            "source_key",
            name="uq_usage_event_source",
        ),
    )
    for column in ("organization_id", "metric", "source_key", "occurred_at"):
        op.create_index(
            op.f(f"ix_usage_events_{column}"),
            "usage_events",
            [column],
            unique=False,
        )

    op.create_table(
        "billing_customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("external_customer_id", sa.String(length=180), nullable=False),
        sa.Column("billing_email", sa.String(length=320), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
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
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_billing_customers_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_customers")),
        sa.UniqueConstraint(
            "organization_id",
            name="uq_billing_customer_organization",
        ),
        sa.UniqueConstraint(
            "provider",
            "external_customer_id",
            name="uq_billing_customer_provider_external",
        ),
    )
    for column in ("organization_id", "provider", "external_customer_id", "status"):
        op.create_index(
            op.f(f"ix_billing_customers_{column}"),
            "billing_customers",
            [column],
            unique=False,
        )

    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("billing_customer_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("external_invoice_id", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount_due_minor", sa.BigInteger(), nullable=False),
        sa.Column("amount_paid_minor", sa.BigInteger(), nullable=False),
        sa.Column("hosted_invoice_url", sa.String(length=1000), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
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
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_billing_invoices_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["billing_customer_id"],
            ["billing_customers.id"],
            name=op.f("fk_billing_invoices_billing_customer_id_billing_customers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_invoices")),
        sa.UniqueConstraint(
            "provider",
            "external_invoice_id",
            name="uq_billing_invoice_provider_external",
        ),
    )
    for column in (
        "organization_id",
        "billing_customer_id",
        "provider",
        "external_invoice_id",
        "status",
        "due_at",
    ):
        op.create_index(
            op.f(f"ix_billing_invoices_{column}"),
            "billing_invoices",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for table, columns in (
        (
            "billing_invoices",
            (
                "due_at",
                "status",
                "external_invoice_id",
                "provider",
                "billing_customer_id",
                "organization_id",
            ),
        ),
        (
            "billing_customers",
            ("status", "external_customer_id", "provider", "organization_id"),
        ),
        (
            "usage_events",
            ("occurred_at", "source_key", "metric", "organization_id"),
        ),
        ("usage_counters", ("status", "period_end", "metric", "organization_id")),
        (
            "organization_entitlements",
            ("expires_at", "value_type", "key", "organization_id"),
        ),
        (
            "organization_subscriptions",
            (
                "current_period_end",
                "trial_ends_at",
                "provider_subscription_id",
                "status",
                "plan_id",
                "organization_id",
            ),
        ),
        ("plan_entitlements", ("value_type", "key", "plan_id")),
        ("plan_prices", ("external_price_id", "status", "plan_id")),
    ):
        for column in columns:
            op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
        op.drop_table(table)

    op.drop_index(op.f("ix_plans_status"), table_name="plans")
    op.drop_index(op.f("ix_plans_key"), table_name="plans")
    op.drop_table("plans")
