"""Add organization application catalog.

Revision ID: 20260611_0003
Revises: 20260611_0002
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0003"
down_revision: str | None = "20260611_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("name_normalized", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("business_owner", sa.String(length=120), nullable=True),
        sa.Column("technical_owner", sa.String(length=120), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_applications"),
        sa.UniqueConstraint(
            "organization_id",
            "name_normalized",
            name="uq_applications_org_name_normalized",
        ),
    )
    op.create_index("ix_applications_organization_id", "applications", ["organization_id"])
    op.create_index("ix_applications_status", "applications", ["status"])
    op.create_table(
        "application_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("external_id", sa.String(length=180), nullable=False),
        sa.Column("observed_name", sa.String(length=180), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_application_sources"),
        sa.UniqueConstraint(
            "organization_id",
            "provider",
            "external_id",
            name="uq_application_sources_external",
        ),
    )
    op.create_index(
        "ix_application_sources_application_id",
        "application_sources",
        ["application_id"],
    )
    op.create_index(
        "ix_application_sources_organization_id",
        "application_sources",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_application_sources_organization_id", table_name="application_sources")
    op.drop_index("ix_application_sources_application_id", table_name="application_sources")
    op.drop_table("application_sources")
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_organization_id", table_name="applications")
    op.drop_table("applications")
