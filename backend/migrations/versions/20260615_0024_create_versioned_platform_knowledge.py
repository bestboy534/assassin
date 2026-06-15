"""create versioned platform knowledge

Revision ID: 20260615_0024
Revises: 20260615_0023
Create Date: 2026-06-15 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260615_0024"
down_revision: str | None = "20260615_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_knowledge_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("object_type", sa.String(length=60), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("published_version_number", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "object_type",
            "key",
            name="uq_platform_knowledge_type_key",
        ),
    )
    for column in (
        "object_type",
        "key",
        "status",
        "published_version_number",
        "created_by_user_id",
    ):
        op.create_index(
            op.f(f"ix_platform_knowledge_entries_{column}"),
            "platform_knowledge_entries",
            [column],
        )

    op.create_table(
        "platform_knowledge_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("published_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["platform_knowledge_entries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["published_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entry_id",
            "version_number",
            name="uq_platform_knowledge_entry_version",
        ),
    )
    for column in (
        "entry_id",
        "status",
        "created_by_user_id",
        "reviewed_by_user_id",
        "published_by_user_id",
    ):
        op.create_index(
            op.f(f"ix_platform_knowledge_versions_{column}"),
            "platform_knowledge_versions",
            [column],
        )


def downgrade() -> None:
    op.drop_table("platform_knowledge_versions")
    op.drop_table("platform_knowledge_entries")
