"""Create vendor master records and risk assessments.

Revision ID: 20260611_0007
Revises: 20260611_0006
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0007"
down_revision: str | None = "20260611_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("normalized_name", sa.String(length=180), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("business_owner", sa.String(length=120), nullable=True),
        sa.Column("risk_owner", sa.String(length=120), nullable=True),
        sa.Column("overall_risk_score", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_vendors"),
        sa.UniqueConstraint(
            "organization_id",
            "normalized_name",
            name="uq_vendors_organization_normalized_name",
        ),
    )
    op.create_index("ix_vendors_organization_id", "vendors", ["organization_id"])
    op.create_index("ix_vendors_status", "vendors", ["status"])
    op.create_index("ix_vendors_risk_level", "vendors", ["risk_level"])

    op.create_table(
        "vendor_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("normalized_alias", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"],
            ["vendors.id"],
            name="fk_vendor_aliases_vendor_id_vendors",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vendor_aliases"),
        sa.UniqueConstraint(
            "organization_id",
            "normalized_alias",
            name="uq_vendor_aliases_organization_normalized_alias",
        ),
    )
    op.create_index("ix_vendor_aliases_organization_id", "vendor_aliases", ["organization_id"])
    op.create_index("ix_vendor_aliases_vendor_id", "vendor_aliases", ["vendor_id"])

    op.create_table(
        "vendor_risk_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), nullable=False),
        sa.Column("questionnaire_version", sa.Integer(), nullable=False),
        sa.Column("rule_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("dimensions_json", sa.Text(), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"],
            ["vendors.id"],
            name="fk_vendor_risk_assessments_vendor_id_vendors",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vendor_risk_assessments"),
    )
    op.create_index(
        "ix_vendor_risk_assessments_organization_id",
        "vendor_risk_assessments",
        ["organization_id"],
    )
    op.create_index(
        "ix_vendor_risk_assessments_vendor_id",
        "vendor_risk_assessments",
        ["vendor_id"],
    )
    op.create_index(
        "ix_vendor_risk_assessments_status",
        "vendor_risk_assessments",
        ["status"],
    )

    op.create_table(
        "risk_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("dimension", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("owner_name", sa.String(length=120), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("mitigation_plan", sa.Text(), nullable=True),
        sa.Column("accepted_reason", sa.Text(), nullable=True),
        sa.Column("accepted_until", sa.Date(), nullable=True),
        sa.Column("accepted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["vendor_risk_assessments.id"],
            name="fk_risk_findings_assessment_id_vendor_risk_assessments",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"],
            ["vendors.id"],
            name="fk_risk_findings_vendor_id_vendors",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_risk_findings"),
    )
    op.create_index("ix_risk_findings_organization_id", "risk_findings", ["organization_id"])
    op.create_index("ix_risk_findings_vendor_id", "risk_findings", ["vendor_id"])
    op.create_index("ix_risk_findings_assessment_id", "risk_findings", ["assessment_id"])
    op.create_index("ix_risk_findings_dimension", "risk_findings", ["dimension"])
    op.create_index("ix_risk_findings_severity", "risk_findings", ["severity"])
    op.create_index("ix_risk_findings_status", "risk_findings", ["status"])
    op.create_index("ix_risk_findings_due_date", "risk_findings", ["due_date"])


def downgrade() -> None:
    op.drop_index("ix_risk_findings_due_date", table_name="risk_findings")
    op.drop_index("ix_risk_findings_status", table_name="risk_findings")
    op.drop_index("ix_risk_findings_severity", table_name="risk_findings")
    op.drop_index("ix_risk_findings_dimension", table_name="risk_findings")
    op.drop_index("ix_risk_findings_assessment_id", table_name="risk_findings")
    op.drop_index("ix_risk_findings_vendor_id", table_name="risk_findings")
    op.drop_index("ix_risk_findings_organization_id", table_name="risk_findings")
    op.drop_table("risk_findings")
    op.drop_index("ix_vendor_risk_assessments_status", table_name="vendor_risk_assessments")
    op.drop_index("ix_vendor_risk_assessments_vendor_id", table_name="vendor_risk_assessments")
    op.drop_index(
        "ix_vendor_risk_assessments_organization_id",
        table_name="vendor_risk_assessments",
    )
    op.drop_table("vendor_risk_assessments")
    op.drop_index("ix_vendor_aliases_vendor_id", table_name="vendor_aliases")
    op.drop_index("ix_vendor_aliases_organization_id", table_name="vendor_aliases")
    op.drop_table("vendor_aliases")
    op.drop_index("ix_vendors_risk_level", table_name="vendors")
    op.drop_index("ix_vendors_status", table_name="vendors")
    op.drop_index("ix_vendors_organization_id", table_name="vendors")
    op.drop_table("vendors")
