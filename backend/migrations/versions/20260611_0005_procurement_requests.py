"""Create procurement request tables.

Revision ID: 20260611_0005
Revises: 20260611_0004
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0005"
down_revision: str | None = "20260611_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("software_name", sa.String(length=180), nullable=False),
        sa.Column("business_reason", sa.Text(), nullable=False),
        sa.Column("estimated_monthly_cost_usd", sa.Float(), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=False),
        sa.Column("handles_sensitive_data", sa.Boolean(), nullable=False),
        sa.Column("data_categories_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_approval_task_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_purchase_requests"),
    )
    op.create_index("ix_purchase_requests_organization_id", "purchase_requests", ["organization_id"])
    op.create_index("ix_purchase_requests_status", "purchase_requests", ["status"])
    op.create_index(
        "ix_purchase_requests_current_approval_task_id",
        "purchase_requests",
        ["current_approval_task_id"],
    )

    op.create_table(
        "approval_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_request_id", sa.Uuid(), nullable=False),
        sa.Column("assignee_role", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["purchase_request_id"],
            ["purchase_requests.id"],
            name="fk_approval_tasks_purchase_request_id_purchase_requests",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_approval_tasks"),
    )
    op.create_index("ix_approval_tasks_organization_id", "approval_tasks", ["organization_id"])
    op.create_index("ix_approval_tasks_purchase_request_id", "approval_tasks", ["purchase_request_id"])
    op.create_index("ix_approval_tasks_status", "approval_tasks", ["status"])

    op.create_table(
        "approval_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("approval_task_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["approval_task_id"],
            ["approval_tasks.id"],
            name="fk_approval_decisions_approval_task_id_approval_tasks",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_approval_decisions"),
        sa.UniqueConstraint(
            "approval_task_id",
            "idempotency_key",
            name="uq_approval_decisions_task_idempotency",
        ),
    )
    op.create_index("ix_approval_decisions_organization_id", "approval_decisions", ["organization_id"])
    op.create_index("ix_approval_decisions_approval_task_id", "approval_decisions", ["approval_task_id"])


def downgrade() -> None:
    op.drop_index("ix_approval_decisions_approval_task_id", table_name="approval_decisions")
    op.drop_index("ix_approval_decisions_organization_id", table_name="approval_decisions")
    op.drop_table("approval_decisions")
    op.drop_index("ix_approval_tasks_status", table_name="approval_tasks")
    op.drop_index("ix_approval_tasks_purchase_request_id", table_name="approval_tasks")
    op.drop_index("ix_approval_tasks_organization_id", table_name="approval_tasks")
    op.drop_table("approval_tasks")
    op.drop_index("ix_purchase_requests_current_approval_task_id", table_name="purchase_requests")
    op.drop_index("ix_purchase_requests_status", table_name="purchase_requests")
    op.drop_index("ix_purchase_requests_organization_id", table_name="purchase_requests")
    op.drop_table("purchase_requests")
