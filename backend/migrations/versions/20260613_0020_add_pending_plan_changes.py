"""add scheduled plan changes

Revision ID: 20260613_0020
Revises: 20260613_0019
Create Date: 2026-06-13 14:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0020"
down_revision: str | None = "20260613_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("organization_subscriptions") as batch_op:
        batch_op.add_column(
            sa.Column("pending_plan_id", sa.Uuid(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "pending_change_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("pending_change_type", sa.String(length=32), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_organization_subscriptions_pending_plan_id_plans",
            "plans",
            ["pending_plan_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            op.f("ix_organization_subscriptions_pending_plan_id"),
            ["pending_plan_id"],
            unique=False,
        )
        batch_op.create_index(
            op.f("ix_organization_subscriptions_pending_change_at"),
            ["pending_change_at"],
            unique=False,
        )
        batch_op.create_index(
            op.f("ix_organization_subscriptions_pending_change_type"),
            ["pending_change_type"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("organization_subscriptions") as batch_op:
        batch_op.drop_index(
            op.f("ix_organization_subscriptions_pending_change_type")
        )
        batch_op.drop_index(
            op.f("ix_organization_subscriptions_pending_change_at")
        )
        batch_op.drop_index(
            op.f("ix_organization_subscriptions_pending_plan_id")
        )
        batch_op.drop_constraint(
            "fk_organization_subscriptions_pending_plan_id_plans",
            type_="foreignkey",
        )
        batch_op.drop_column("pending_change_type")
        batch_op.drop_column("pending_change_at")
        batch_op.drop_column("pending_plan_id")
