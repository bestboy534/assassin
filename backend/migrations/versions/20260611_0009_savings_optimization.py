"""Create savings opportunities, optimization projects, and verified results.

Revision ID: 20260611_0009
Revises: 20260611_0008
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0009"
down_revision: str | None = "20260611_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "savings_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=180), nullable=False),
        sa.Column("rule_version", sa.String(length=80), nullable=False),
        sa.Column("period_key", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("estimated_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_savings_opportunities"),
        sa.UniqueConstraint(
            "organization_id",
            "source_type",
            "source_id",
            "rule_version",
            "period_key",
            name="uq_savings_opportunities_source",
        ),
    )
    op.create_index(
        "ix_savings_opportunities_organization_id",
        "savings_opportunities",
        ["organization_id"],
    )
    op.create_index(
        "ix_savings_opportunities_department",
        "savings_opportunities",
        ["department"],
    )
    op.create_index(
        "ix_savings_opportunities_category",
        "savings_opportunities",
        ["category"],
    )
    op.create_index(
        "ix_savings_opportunities_status",
        "savings_opportunities",
        ["status"],
    )

    op.create_table(
        "savings_baselines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("monthly_cost", sa.Numeric(19, 4), nullable=False),
        sa.Column("calculation_months", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("calculation_method", sa.String(length=80), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("contract_end", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["savings_opportunities.id"],
            name="fk_savings_baselines_opportunity_id_savings_opportunities",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_savings_baselines"),
        sa.UniqueConstraint("opportunity_id", name="uq_savings_baselines_opportunity_id"),
    )
    op.create_index(
        "ix_savings_baselines_organization_id",
        "savings_baselines",
        ["organization_id"],
    )

    op.create_table(
        "optimization_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("owner_name", sa.String(length=120), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("target_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["savings_opportunities.id"],
            name="fk_optimization_projects_opportunity_id_savings_opportunities",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_optimization_projects"),
        sa.UniqueConstraint("opportunity_id", name="uq_optimization_projects_opportunity_id"),
    )
    op.create_index(
        "ix_optimization_projects_organization_id",
        "optimization_projects",
        ["organization_id"],
    )

    op.create_table(
        "optimization_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["optimization_projects.id"],
            name="fk_optimization_tasks_project_id_optimization_projects",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_optimization_tasks"),
    )
    op.create_index(
        "ix_optimization_tasks_organization_id",
        "optimization_tasks",
        ["organization_id"],
    )
    op.create_index(
        "ix_optimization_tasks_project_id",
        "optimization_tasks",
        ["project_id"],
    )

    op.create_table(
        "savings_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("new_monthly_cost", sa.Numeric(19, 4), nullable=False),
        sa.Column("realized_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("verified_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("realization_evidence", sa.Text(), nullable=False),
        sa.Column("verification_evidence_json", sa.Text(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["optimization_projects.id"],
            name="fk_savings_results_project_id_optimization_projects",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_savings_results"),
        sa.UniqueConstraint("project_id", name="uq_savings_results_project_id"),
    )
    op.create_index(
        "ix_savings_results_organization_id",
        "savings_results",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_savings_results_organization_id", table_name="savings_results")
    op.drop_table("savings_results")
    op.drop_index("ix_optimization_tasks_project_id", table_name="optimization_tasks")
    op.drop_index("ix_optimization_tasks_organization_id", table_name="optimization_tasks")
    op.drop_table("optimization_tasks")
    op.drop_index("ix_optimization_projects_organization_id", table_name="optimization_projects")
    op.drop_table("optimization_projects")
    op.drop_index("ix_savings_baselines_organization_id", table_name="savings_baselines")
    op.drop_table("savings_baselines")
    op.drop_index("ix_savings_opportunities_status", table_name="savings_opportunities")
    op.drop_index("ix_savings_opportunities_category", table_name="savings_opportunities")
    op.drop_index("ix_savings_opportunities_department", table_name="savings_opportunities")
    op.drop_index(
        "ix_savings_opportunities_organization_id",
        table_name="savings_opportunities",
    )
    op.drop_table("savings_opportunities")
