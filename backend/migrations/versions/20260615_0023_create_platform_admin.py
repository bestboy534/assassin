"""create controlled platform administration

Revision ID: 20260615_0023
Revises: 20260615_0022
Create Date: 2026-06-15 13:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260615_0023"
down_revision: str | None = "20260615_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("platform_role", sa.String(length=40), nullable=True),
    )
    op.create_index(
        op.f("ix_users_platform_role"),
        "users",
        ["platform_role"],
    )

    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("rollout_percentage", sa.Integer(), nullable=False),
        sa.Column("organization_allowlist_json", sa.JSON(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feature_flags_key"),
        "feature_flags",
        ["key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_feature_flags_status"),
        "feature_flags",
        ["status"],
    )

    op.create_table(
        "email_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider_message_id", sa.String(length=180), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "organization_id",
        "template_key",
        "recipient",
        "status",
        "provider_message_id",
        "created_at",
    ):
        op.create_index(
            op.f(f"ix_email_deliveries_{column}"),
            "email_deliveries",
            [column],
        )

    op.create_table(
        "platform_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=180), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=False),
        sa.Column("after_json", sa.JSON(), nullable=False),
        sa.Column(
            "reauth_confirmed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "actor_type",
        "actor_user_id",
        "action",
        "resource_type",
        "resource_id",
        "created_at",
    ):
        op.create_index(
            op.f(f"ix_platform_audit_logs_{column}"),
            "platform_audit_logs",
            [column],
        )
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(
            """
            CREATE TRIGGER platform_audit_logs_no_update
            BEFORE UPDATE ON platform_audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'platform_audit_logs are immutable');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER platform_audit_logs_no_delete
            BEFORE DELETE ON platform_audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'platform_audit_logs are immutable');
            END
            """
        )
    elif bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_platform_audit_logs_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'platform_audit_logs are immutable';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER platform_audit_logs_no_mutation
            BEFORE UPDATE OR DELETE ON platform_audit_logs
            FOR EACH ROW EXECUTE FUNCTION prevent_platform_audit_logs_mutation();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS platform_audit_logs_no_update")
        op.execute("DROP TRIGGER IF EXISTS platform_audit_logs_no_delete")
    elif bind.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS platform_audit_logs_no_mutation "
            "ON platform_audit_logs"
        )
        op.execute(
            "DROP FUNCTION IF EXISTS prevent_platform_audit_logs_mutation()"
        )
    op.drop_table("platform_audit_logs")
    op.drop_table("email_deliveries")
    op.drop_table("feature_flags")
    op.drop_index(op.f("ix_users_platform_role"), table_name="users")
    op.drop_column("users", "platform_role")
