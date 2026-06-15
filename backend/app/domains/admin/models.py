from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DDL, JSON, DateTime, ForeignKey, Integer, String, Uuid, event, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import new_uuid


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="disabled",
        index=True,
    )
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    organization_allowlist_json: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        index=True,
    )
    template_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="pending",
        index=True,
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(180), index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatformAuditLog(Base):
    __tablename__ = "platform_audit_logs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    actor_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="user",
        index=True,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    before_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    after_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reauth_confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )


event.listen(
    PlatformAuditLog.__table__,
    "after_create",
    DDL(  # type: ignore[no-untyped-call]
        """
        CREATE TRIGGER platform_audit_logs_no_update
        BEFORE UPDATE ON platform_audit_logs
        BEGIN
            SELECT RAISE(ABORT, 'platform_audit_logs are immutable');
        END
        """
    ).execute_if(dialect="sqlite"),
)
event.listen(
    PlatformAuditLog.__table__,
    "after_create",
    DDL(  # type: ignore[no-untyped-call]
        """
        CREATE TRIGGER platform_audit_logs_no_delete
        BEFORE DELETE ON platform_audit_logs
        BEGIN
            SELECT RAISE(ABORT, 'platform_audit_logs are immutable');
        END
        """
    ).execute_if(dialect="sqlite"),
)
event.listen(
    PlatformAuditLog.__table__,
    "after_create",
    DDL(  # type: ignore[no-untyped-call]
        """
        CREATE OR REPLACE FUNCTION prevent_platform_audit_logs_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'platform_audit_logs are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    PlatformAuditLog.__table__,
    "after_create",
    DDL(  # type: ignore[no-untyped-call]
        """
        CREATE TRIGGER platform_audit_logs_no_mutation
        BEFORE UPDATE OR DELETE ON platform_audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_platform_audit_logs_mutation();
        """
    ).execute_if(dialect="postgresql"),
)
