"""Create contracts, versions, and renewals.

Revision ID: 20260611_0006
Revises: 20260611_0005
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0006"
down_revision: str | None = "20260611_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("vendor_name", sa.String(length=180), nullable=False),
        sa.Column("application_name", sa.String(length=180), nullable=True),
        sa.Column("owner_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_contracts"),
    )
    op.create_index("ix_contracts_organization_id", "contracts", ["organization_id"])
    op.create_index("ix_contracts_status", "contracts", ["status"])
    op.create_index("ix_contracts_current_version_id", "contracts", ["current_version_id"])

    op.create_table(
        "contract_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("billing_frequency", sa.String(length=32), nullable=False),
        sa.Column("auto_renew", sa.Boolean(), nullable=False),
        sa.Column("notice_period_days", sa.Integer(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            name="fk_contract_versions_contract_id_contracts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_contract_versions"),
        sa.UniqueConstraint(
            "contract_id",
            "version_number",
            name="uq_contract_versions_contract_number",
        ),
    )
    op.create_index(
        "ix_contract_versions_organization_id",
        "contract_versions",
        ["organization_id"],
    )
    op.create_index("ix_contract_versions_contract_id", "contract_versions", ["contract_id"])
    op.create_index("ix_contract_versions_status", "contract_versions", ["status"])

    op.create_table(
        "renewals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("source_version_id", sa.Uuid(), nullable=False),
        sa.Column("renewal_date", sa.Date(), nullable=False),
        sa.Column("decision_deadline", sa.Date(), nullable=False),
        sa.Column("owner_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("current_amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            name="fk_renewals_contract_id_contracts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["contract_versions.id"],
            name="fk_renewals_source_version_id_contract_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_renewals"),
        sa.UniqueConstraint(
            "contract_id",
            "source_version_id",
            name="uq_renewals_contract_version",
        ),
    )
    op.create_index("ix_renewals_organization_id", "renewals", ["organization_id"])
    op.create_index("ix_renewals_contract_id", "renewals", ["contract_id"])
    op.create_index("ix_renewals_source_version_id", "renewals", ["source_version_id"])
    op.create_index("ix_renewals_renewal_date", "renewals", ["renewal_date"])
    op.create_index("ix_renewals_decision_deadline", "renewals", ["decision_deadline"])
    op.create_index("ix_renewals_status", "renewals", ["status"])


def downgrade() -> None:
    op.drop_index("ix_renewals_status", table_name="renewals")
    op.drop_index("ix_renewals_decision_deadline", table_name="renewals")
    op.drop_index("ix_renewals_renewal_date", table_name="renewals")
    op.drop_index("ix_renewals_source_version_id", table_name="renewals")
    op.drop_index("ix_renewals_contract_id", table_name="renewals")
    op.drop_index("ix_renewals_organization_id", table_name="renewals")
    op.drop_table("renewals")
    op.drop_index("ix_contract_versions_status", table_name="contract_versions")
    op.drop_index("ix_contract_versions_contract_id", table_name="contract_versions")
    op.drop_index("ix_contract_versions_organization_id", table_name="contract_versions")
    op.drop_table("contract_versions")
    op.drop_index("ix_contracts_current_version_id", table_name="contracts")
    op.drop_index("ix_contracts_status", table_name="contracts")
    op.drop_index("ix_contracts_organization_id", table_name="contracts")
    op.drop_table("contracts")
