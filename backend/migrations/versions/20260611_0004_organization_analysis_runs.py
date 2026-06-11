"""Attach analysis runs to organizations.

Revision ID: 20260611_0004
Revises: 20260611_0003
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0004"
down_revision: str | None = "20260611_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("analysis_runs", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.add_column("analysis_runs", sa.Column("created_by_user_id", sa.Uuid(), nullable=True))
    op.add_column(
        "analysis_runs",
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="completed",
            nullable=False,
        ),
    )
    op.add_column(
        "analysis_runs",
        sa.Column(
            "total_monthly_cost_usd",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
    )
    op.create_index("ix_analysis_runs_organization_id", "analysis_runs", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_runs_organization_id", table_name="analysis_runs")
    op.drop_column("analysis_runs", "total_monthly_cost_usd")
    op.drop_column("analysis_runs", "status")
    op.drop_column("analysis_runs", "created_by_user_id")
    op.drop_column("analysis_runs", "organization_id")
