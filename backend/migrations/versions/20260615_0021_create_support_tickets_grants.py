"""create support tickets and time bounded grants

Revision ID: 20260615_0021
Revises: 20260613_0020
Create Date: 2026-06-15 09:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260615_0021"
down_revision: str | None = "20260613_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("priority", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("support_tier", sa.String(length=32), nullable=False),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("first_response_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_paused_seconds", sa.Integer(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "organization_id",
        "created_by_user_id",
        "category",
        "priority",
        "status",
        "first_response_due_at",
        "resolution_due_at",
        "resolved_at",
        "closed_at",
        "created_at",
    ):
        op.create_index(op.f(f"ix_support_tickets_{column}"), "support_tickets", [column])

    op.create_table(
        "support_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("support_ticket_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=True),
        sa.Column("author_type", sa.String(length=24), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("internal", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["support_ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "organization_id",
        "support_ticket_id",
        "author_user_id",
        "author_type",
        "created_at",
    ):
        op.create_index(op.f(f"ix_support_messages_{column}"), "support_messages", [column])

    op.create_table(
        "support_sla_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("support_ticket_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("target_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["support_ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "organization_id",
        "support_ticket_id",
        "event_type",
        "target_at",
        "created_at",
    ):
        op.create_index(op.f(f"ix_support_sla_events_{column}"), "support_sla_events", [column])

    op.create_table(
        "support_satisfaction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("support_ticket_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["support_ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("support_ticket_id", name="uq_support_satisfaction_ticket"),
    )
    for column in ("organization_id", "support_ticket_id", "submitted_by_user_id"):
        op.create_index(op.f(f"ix_support_satisfaction_{column}"), "support_satisfaction", [column])

    op.create_table(
        "support_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("support_user_id", sa.Uuid(), nullable=False),
        sa.Column("scopes_json", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["support_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "organization_id",
        "support_user_id",
        "approved_by_user_id",
        "expires_at",
        "revoked_at",
        "created_at",
    ):
        op.create_index(op.f(f"ix_support_grants_{column}"), "support_grants", [column])

    op.create_table(
        "support_access_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("support_grant_id", sa.Uuid(), nullable=False),
        sa.Column("support_user_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=180), nullable=True),
        sa.Column("purpose", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["support_grant_id"], ["support_grants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["support_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "organization_id",
        "support_grant_id",
        "support_user_id",
        "scope",
        "resource_type",
        "resource_id",
        "created_at",
    ):
        op.create_index(op.f(f"ix_support_access_logs_{column}"), "support_access_logs", [column])

    op.create_table(
        "support_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("support_ticket_id", sa.Uuid(), nullable=False),
        sa.Column("support_message_id", sa.Uuid(), nullable=True),
        sa.Column("stored_file_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=260), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stored_file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["support_message_id"], ["support_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["support_ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "organization_id",
        "support_ticket_id",
        "support_message_id",
        "stored_file_id",
    ):
        op.create_index(op.f(f"ix_support_attachments_{column}"), "support_attachments", [column])


def downgrade() -> None:
    for table in (
        "support_attachments",
        "support_access_logs",
        "support_grants",
        "support_satisfaction",
        "support_sla_events",
        "support_messages",
        "support_tickets",
    ):
        op.drop_table(table)
