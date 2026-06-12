from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DDL, JSON, DateTime, String, Uuid, event, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import new_uuid


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    actor_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    before_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    after_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )


event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(  # type: ignore[no-untyped-call]
        """
        CREATE TRIGGER audit_logs_no_update
        BEFORE UPDATE ON audit_logs
        BEGIN
            SELECT RAISE(ABORT, 'audit_logs are immutable');
        END
        """
    ).execute_if(dialect="sqlite"),
)
event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(  # type: ignore[no-untyped-call]
        """
        CREATE TRIGGER audit_logs_no_delete
        BEFORE DELETE ON audit_logs
        BEGIN
            SELECT RAISE(ABORT, 'audit_logs are immutable');
        END
        """
    ).execute_if(dialect="sqlite"),
)
event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(  # type: ignore[no-untyped-call]
        """
        CREATE OR REPLACE FUNCTION prevent_audit_logs_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(  # type: ignore[no-untyped-call]
        """
        CREATE TRIGGER audit_logs_no_mutation
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_logs_mutation();
        """
    ).execute_if(dialect="postgresql"),
)
