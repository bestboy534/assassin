"""create retention deletion

Revision ID: 20260612_0015
Revises: 20260612_0014
Create Date: 2026-06-12 15:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_0015"
down_revision: str | None = "20260612_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retention_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("data_type", sa.String(length=80), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retention_policies")),
    )
    op.create_index(op.f("ix_retention_policies_action"), "retention_policies", ["action"], unique=False)
    op.create_index(op.f("ix_retention_policies_created_by_user_id"), "retention_policies", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_retention_policies_data_type"), "retention_policies", ["data_type"], unique=False)
    op.create_index(op.f("ix_retention_policies_organization_id"), "retention_policies", ["organization_id"], unique=False)
    op.create_index(op.f("ix_retention_policies_status"), "retention_policies", ["status"], unique=False)

    op.create_table(
        "legal_holds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=160), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_holds")),
    )
    op.create_index(op.f("ix_legal_holds_created_by_user_id"), "legal_holds", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_legal_holds_organization_id"), "legal_holds", ["organization_id"], unique=False)
    op.create_index(op.f("ix_legal_holds_resource_id"), "legal_holds", ["resource_id"], unique=False)
    op.create_index(op.f("ix_legal_holds_resource_type"), "legal_holds", ["resource_type"], unique=False)
    op.create_index(op.f("ix_legal_holds_status"), "legal_holds", ["status"], unique=False)

    op.create_table(
        "deletion_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("data_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reauth_confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deletion_jobs")),
    )
    op.create_index(op.f("ix_deletion_jobs_data_type"), "deletion_jobs", ["data_type"], unique=False)
    op.create_index(op.f("ix_deletion_jobs_organization_id"), "deletion_jobs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_deletion_jobs_requested_by_user_id"), "deletion_jobs", ["requested_by_user_id"], unique=False)
    op.create_index(op.f("ix_deletion_jobs_status"), "deletion_jobs", ["status"], unique=False)

    op.create_table(
        "deletion_job_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("deletion_job_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=160), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["deletion_job_id"],
            ["deletion_jobs.id"],
            name=op.f("fk_deletion_job_items_deletion_job_id_deletion_jobs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deletion_job_items")),
    )
    op.create_index(op.f("ix_deletion_job_items_action"), "deletion_job_items", ["action"], unique=False)
    op.create_index(op.f("ix_deletion_job_items_deletion_job_id"), "deletion_job_items", ["deletion_job_id"], unique=False)
    op.create_index(op.f("ix_deletion_job_items_organization_id"), "deletion_job_items", ["organization_id"], unique=False)
    op.create_index(op.f("ix_deletion_job_items_resource_id"), "deletion_job_items", ["resource_id"], unique=False)
    op.create_index(op.f("ix_deletion_job_items_resource_type"), "deletion_job_items", ["resource_type"], unique=False)
    op.create_index(op.f("ix_deletion_job_items_status"), "deletion_job_items", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_deletion_job_items_status"), table_name="deletion_job_items")
    op.drop_index(op.f("ix_deletion_job_items_resource_type"), table_name="deletion_job_items")
    op.drop_index(op.f("ix_deletion_job_items_resource_id"), table_name="deletion_job_items")
    op.drop_index(op.f("ix_deletion_job_items_organization_id"), table_name="deletion_job_items")
    op.drop_index(op.f("ix_deletion_job_items_deletion_job_id"), table_name="deletion_job_items")
    op.drop_index(op.f("ix_deletion_job_items_action"), table_name="deletion_job_items")
    op.drop_table("deletion_job_items")
    op.drop_index(op.f("ix_deletion_jobs_status"), table_name="deletion_jobs")
    op.drop_index(op.f("ix_deletion_jobs_requested_by_user_id"), table_name="deletion_jobs")
    op.drop_index(op.f("ix_deletion_jobs_organization_id"), table_name="deletion_jobs")
    op.drop_index(op.f("ix_deletion_jobs_data_type"), table_name="deletion_jobs")
    op.drop_table("deletion_jobs")
    op.drop_index(op.f("ix_legal_holds_status"), table_name="legal_holds")
    op.drop_index(op.f("ix_legal_holds_resource_type"), table_name="legal_holds")
    op.drop_index(op.f("ix_legal_holds_resource_id"), table_name="legal_holds")
    op.drop_index(op.f("ix_legal_holds_organization_id"), table_name="legal_holds")
    op.drop_index(op.f("ix_legal_holds_created_by_user_id"), table_name="legal_holds")
    op.drop_table("legal_holds")
    op.drop_index(op.f("ix_retention_policies_status"), table_name="retention_policies")
    op.drop_index(op.f("ix_retention_policies_organization_id"), table_name="retention_policies")
    op.drop_index(op.f("ix_retention_policies_data_type"), table_name="retention_policies")
    op.drop_index(op.f("ix_retention_policies_created_by_user_id"), table_name="retention_policies")
    op.drop_index(op.f("ix_retention_policies_action"), table_name="retention_policies")
    op.drop_table("retention_policies")
