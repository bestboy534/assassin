"""create privacy requests

Revision ID: 20260612_0016
Revises: 20260612_0015
Create Date: 2026-06-12 16:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_0016"
down_revision: str | None = "20260612_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_user_id", sa.Uuid(), nullable=False),
        sa.Column("request_type", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("identity_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("requested_changes_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["subject_user_id"],
            ["users.id"],
            name=op.f("fk_privacy_requests_subject_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_privacy_requests")),
    )
    op.create_index(
        op.f("ix_privacy_requests_due_at"),
        "privacy_requests",
        ["due_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_privacy_requests_request_type"),
        "privacy_requests",
        ["request_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_privacy_requests_status"),
        "privacy_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_privacy_requests_subject_user_id"),
        "privacy_requests",
        ["subject_user_id"],
        unique=False,
    )

    op.create_table(
        "privacy_request_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("privacy_request_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["privacy_request_id"],
            ["privacy_requests.id"],
            name=op.f(
                "fk_privacy_request_actions_privacy_request_id_privacy_requests"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_privacy_request_actions")),
    )
    op.create_index(
        op.f("ix_privacy_request_actions_action"),
        "privacy_request_actions",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_privacy_request_actions_actor_user_id"),
        "privacy_request_actions",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_privacy_request_actions_privacy_request_id"),
        "privacy_request_actions",
        ["privacy_request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_privacy_request_actions_privacy_request_id"),
        table_name="privacy_request_actions",
    )
    op.drop_index(
        op.f("ix_privacy_request_actions_actor_user_id"),
        table_name="privacy_request_actions",
    )
    op.drop_index(
        op.f("ix_privacy_request_actions_action"),
        table_name="privacy_request_actions",
    )
    op.drop_table("privacy_request_actions")
    op.drop_index(
        op.f("ix_privacy_requests_subject_user_id"),
        table_name="privacy_requests",
    )
    op.drop_index(op.f("ix_privacy_requests_status"), table_name="privacy_requests")
    op.drop_index(
        op.f("ix_privacy_requests_request_type"),
        table_name="privacy_requests",
    )
    op.drop_index(op.f("ix_privacy_requests_due_at"), table_name="privacy_requests")
    op.drop_table("privacy_requests")
