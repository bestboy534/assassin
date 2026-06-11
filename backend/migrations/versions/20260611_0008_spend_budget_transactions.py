"""Create budgets, precise transactions, anomalies, and accounting periods.

Revision ID: 20260611_0008
Revises: 20260611_0007
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0008"
down_revision: str | None = "20260611_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_budgets"),
        sa.UniqueConstraint(
            "organization_id",
            "fiscal_year",
            "department",
            "currency",
            name="uq_budgets_org_year_department_currency",
        ),
    )
    op.create_index("ix_budgets_organization_id", "budgets", ["organization_id"])
    op.create_index("ix_budgets_fiscal_year", "budgets", ["fiscal_year"])
    op.create_index("ix_budgets_department", "budgets", ["department"])
    op.create_index("ix_budgets_status", "budgets", ["status"])

    op.create_table(
        "budget_commitments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("budget_id", sa.Uuid(), nullable=False),
        sa.Column("commitment_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["budget_id"],
            ["budgets.id"],
            name="fk_budget_commitments_budget_id_budgets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_budget_commitments"),
    )
    op.create_index(
        "ix_budget_commitments_organization_id",
        "budget_commitments",
        ["organization_id"],
    )
    op.create_index("ix_budget_commitments_budget_id", "budget_commitments", ["budget_id"])
    op.create_index(
        "ix_budget_commitments_commitment_type",
        "budget_commitments",
        ["commitment_type"],
    )

    op.create_table(
        "spend_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_provider", sa.String(length=80), nullable=False),
        sa.Column("source_account_id", sa.String(length=120), nullable=False),
        sa.Column("external_id", sa.String(length=180), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("merchant_name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("match_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_spend_transactions"),
        sa.UniqueConstraint(
            "organization_id",
            "source_provider",
            "source_account_id",
            "external_id",
            name="uq_spend_transactions_source",
        ),
    )
    op.create_index(
        "ix_spend_transactions_organization_id",
        "spend_transactions",
        ["organization_id"],
    )
    op.create_index(
        "ix_spend_transactions_transaction_date",
        "spend_transactions",
        ["transaction_date"],
    )
    op.create_index(
        "ix_spend_transactions_department",
        "spend_transactions",
        ["department"],
    )
    op.create_index("ix_spend_transactions_category", "spend_transactions", ["category"])
    op.create_index(
        "ix_spend_transactions_application_id",
        "spend_transactions",
        ["application_id"],
    )

    op.create_table(
        "transaction_splits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["spend_transactions.id"],
            name="fk_transaction_splits_transaction_id_spend_transactions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transaction_splits"),
    )
    op.create_index(
        "ix_transaction_splits_organization_id",
        "transaction_splits",
        ["organization_id"],
    )
    op.create_index(
        "ix_transaction_splits_transaction_id",
        "transaction_splits",
        ["transaction_id"],
    )

    op.create_table(
        "transaction_anomalies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("budget_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("rule_version", sa.String(length=80), nullable=False),
        sa.Column("baseline_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("observed_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["budget_id"],
            ["budgets.id"],
            name="fk_transaction_anomalies_budget_id_budgets",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["spend_transactions.id"],
            name="fk_transaction_anomalies_transaction_id_spend_transactions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transaction_anomalies"),
        sa.UniqueConstraint(
            "transaction_id",
            "code",
            "rule_version",
            name="uq_transaction_anomalies_rule",
        ),
    )
    op.create_index(
        "ix_transaction_anomalies_organization_id",
        "transaction_anomalies",
        ["organization_id"],
    )
    op.create_index(
        "ix_transaction_anomalies_transaction_id",
        "transaction_anomalies",
        ["transaction_id"],
    )
    op.create_index(
        "ix_transaction_anomalies_budget_id",
        "transaction_anomalies",
        ["budget_id"],
    )
    op.create_index("ix_transaction_anomalies_code", "transaction_anomalies", ["code"])
    op.create_index(
        "ix_transaction_anomalies_status",
        "transaction_anomalies",
        ["status"],
    )

    op.create_table(
        "accounting_periods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("locked_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accounting_periods"),
        sa.UniqueConstraint(
            "organization_id",
            "start_date",
            "end_date",
            name="uq_accounting_periods_org_range",
        ),
    )
    op.create_index(
        "ix_accounting_periods_organization_id",
        "accounting_periods",
        ["organization_id"],
    )
    op.create_index(
        "ix_accounting_periods_start_date",
        "accounting_periods",
        ["start_date"],
    )
    op.create_index(
        "ix_accounting_periods_end_date",
        "accounting_periods",
        ["end_date"],
    )
    op.create_index("ix_accounting_periods_status", "accounting_periods", ["status"])


def downgrade() -> None:
    op.drop_index("ix_accounting_periods_status", table_name="accounting_periods")
    op.drop_index("ix_accounting_periods_end_date", table_name="accounting_periods")
    op.drop_index("ix_accounting_periods_start_date", table_name="accounting_periods")
    op.drop_index("ix_accounting_periods_organization_id", table_name="accounting_periods")
    op.drop_table("accounting_periods")
    op.drop_index("ix_transaction_anomalies_status", table_name="transaction_anomalies")
    op.drop_index("ix_transaction_anomalies_code", table_name="transaction_anomalies")
    op.drop_index("ix_transaction_anomalies_budget_id", table_name="transaction_anomalies")
    op.drop_index("ix_transaction_anomalies_transaction_id", table_name="transaction_anomalies")
    op.drop_index("ix_transaction_anomalies_organization_id", table_name="transaction_anomalies")
    op.drop_table("transaction_anomalies")
    op.drop_index("ix_transaction_splits_transaction_id", table_name="transaction_splits")
    op.drop_index("ix_transaction_splits_organization_id", table_name="transaction_splits")
    op.drop_table("transaction_splits")
    op.drop_index("ix_spend_transactions_application_id", table_name="spend_transactions")
    op.drop_index("ix_spend_transactions_category", table_name="spend_transactions")
    op.drop_index("ix_spend_transactions_department", table_name="spend_transactions")
    op.drop_index("ix_spend_transactions_transaction_date", table_name="spend_transactions")
    op.drop_index("ix_spend_transactions_organization_id", table_name="spend_transactions")
    op.drop_table("spend_transactions")
    op.drop_index("ix_budget_commitments_commitment_type", table_name="budget_commitments")
    op.drop_index("ix_budget_commitments_budget_id", table_name="budget_commitments")
    op.drop_index("ix_budget_commitments_organization_id", table_name="budget_commitments")
    op.drop_table("budget_commitments")
    op.drop_index("ix_budgets_status", table_name="budgets")
    op.drop_index("ix_budgets_department", table_name="budgets")
    op.drop_index("ix_budgets_fiscal_year", table_name="budgets")
    op.drop_index("ix_budgets_organization_id", table_name="budgets")
    op.drop_table("budgets")
