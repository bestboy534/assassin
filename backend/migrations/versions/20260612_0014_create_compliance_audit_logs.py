"""create compliance audit logs

Revision ID: 20260612_0014
Revises: 20260612_0013
Create Date: 2026-06-12 14:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_0014"
down_revision: str | None = "20260612_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=160), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=120), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=False),
        sa.Column("after_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor_id"), "audit_logs", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor_type"), "audit_logs", ["actor_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_organization_id"), "audit_logs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_request_id"), "audit_logs", ["request_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_resource_id"), "audit_logs", ["resource_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_resource_type"), "audit_logs", ["resource_type"], unique=False)
    _create_immutability_guards()


def downgrade() -> None:
    _drop_immutability_guards()
    op.drop_index(op.f("ix_audit_logs_resource_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_resource_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_request_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_organization_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")


def _create_immutability_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER audit_logs_no_update
            BEFORE UPDATE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'audit_logs are immutable');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER audit_logs_no_delete
            BEFORE DELETE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'audit_logs are immutable');
            END
            """
        )
    elif dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_audit_logs_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_logs are immutable';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER audit_logs_no_mutation
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_logs_mutation();
            """
        )


def _drop_immutability_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update")
        op.execute("DROP TRIGGER IF EXISTS audit_logs_no_delete")
    elif dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_logs_no_mutation ON audit_logs")
        op.execute("DROP FUNCTION IF EXISTS prevent_audit_logs_mutation()")
