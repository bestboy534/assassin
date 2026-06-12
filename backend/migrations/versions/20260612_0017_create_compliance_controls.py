"""create compliance controls and incidents

Revision ID: 20260612_0017
Revises: 20260612_0016
Create Date: 2026-06-12 18:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_0017"
down_revision: str | None = "20260612_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compliance_frameworks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_compliance_frameworks")),
        sa.UniqueConstraint("organization_id", "code", "version", name="uq_compliance_framework_org_code_version"),
    )
    for column in ("organization_id", "created_by_user_id", "code", "status"):
        op.create_index(op.f(f"ix_compliance_frameworks_{column}"), "compliance_frameworks", [column], unique=False)

    op.create_table(
        "compliance_controls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("framework_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.String(length=3000), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("frequency_days", sa.Integer(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["framework_id"], ["compliance_frameworks.id"], name=op.f("fk_compliance_controls_framework_id_compliance_frameworks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_compliance_controls")),
        sa.UniqueConstraint("framework_id", "code", name="uq_compliance_control_framework_code"),
    )
    for column in ("organization_id", "framework_id", "code", "status", "next_review_at"):
        op.create_index(op.f(f"ix_compliance_controls_{column}"), "compliance_controls", [column], unique=False)

    op.create_table(
        "control_owners",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("control_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["control_id"], ["compliance_controls.id"], name=op.f("fk_control_owners_control_id_compliance_controls"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_control_owners")),
        sa.UniqueConstraint("control_id", "user_id", "role", name="uq_control_owner_role"),
    )
    for column in ("organization_id", "control_id", "user_id", "role"):
        op.create_index(op.f(f"ix_control_owners_{column}"), "control_owners", [column], unique=False)

    op.create_table(
        "control_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("control_id", sa.Uuid(), nullable=False),
        sa.Column("stored_file_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["control_id"], ["compliance_controls.id"], name=op.f("fk_control_evidence_control_id_compliance_controls"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stored_file_id"], ["files.id"], name=op.f("fk_control_evidence_stored_file_id_files"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_control_evidence")),
    )
    for column in ("organization_id", "control_id", "stored_file_id", "uploaded_by_user_id", "status", "expires_at"):
        op.create_index(op.f(f"ix_control_evidence_{column}"), "control_evidence", [column], unique=False)

    op.create_table(
        "control_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("control_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.String(length=3000), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["control_id"], ["compliance_controls.id"], name=op.f("fk_control_reviews_control_id_compliance_controls"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_control_reviews")),
    )
    for column in ("organization_id", "control_id", "reviewer_user_id", "outcome"):
        op.create_index(op.f(f"ix_control_reviews_{column}"), "control_reviews", [column], unique=False)

    op.create_table(
        "security_incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("summary", sa.String(length=4000), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_security_incidents")),
    )
    for column in ("organization_id", "created_by_user_id", "severity", "status"):
        op.create_index(op.f(f"ix_security_incidents_{column}"), "security_incidents", [column], unique=False)

    op.create_table(
        "incident_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("assignee_user_id", sa.Uuid(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["security_incidents.id"], name=op.f("fk_incident_tasks_incident_id_security_incidents"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_tasks")),
    )
    for column in ("organization_id", "incident_id", "status", "assignee_user_id"):
        op.create_index(op.f(f"ix_incident_tasks_{column}"), "incident_tasks", [column], unique=False)


def downgrade() -> None:
    for table, columns in (
        ("incident_tasks", ("assignee_user_id", "status", "incident_id", "organization_id")),
        ("security_incidents", ("status", "severity", "created_by_user_id", "organization_id")),
    ):
        for column in columns:
            op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
        op.drop_table(table)
    for table, columns in (
        ("control_reviews", ("outcome", "reviewer_user_id", "control_id", "organization_id")),
        ("control_evidence", ("expires_at", "status", "uploaded_by_user_id", "stored_file_id", "control_id", "organization_id")),
        ("control_owners", ("role", "user_id", "control_id", "organization_id")),
        ("compliance_controls", ("next_review_at", "status", "code", "framework_id", "organization_id")),
        ("compliance_frameworks", ("status", "code", "created_by_user_id", "organization_id")),
    ):
        for column in columns:
            op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
        op.drop_table(table)
