import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.organizations.service import OrganizationContext

from .models import AuditLog
from .schemas import AuditLogExportResponse, AuditLogResponse

AUDIT_READ_ROLES = {"owner", "admin", "security", "security_admin", "auditor"}
REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = (
    "authorization",
    "card_number",
    "cookie",
    "cvv",
    "full_card",
    "passphrase",
    "password",
    "raw_bill",
    "raw_text",
    "secret",
    "token",
)


class AuditLogForbidden(Exception):
    pass


class AuditLogNotFound(Exception):
    pass


@dataclass(frozen=True)
class AuditLogCreate:
    organization_id: UUID
    actor_type: str
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    before: dict[str, Any] = field(default_factory=dict)
    after: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ComplianceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_audit_log(self, body: AuditLogCreate) -> AuditLog:
        audit_log = AuditLog(
            organization_id=body.organization_id,
            actor_type=body.actor_type,
            actor_id=body.actor_id,
            action=body.action,
            resource_type=body.resource_type,
            resource_id=body.resource_id,
            ip_address=body.ip_address,
            user_agent_hash=_hash_user_agent(body.user_agent),
            request_id=body.request_id,
            before_json=redact_sensitive_values(body.before),
            after_json=redact_sensitive_values(body.after),
            metadata_json=redact_sensitive_values(body.metadata),
        )
        async with transaction(self.session):
            self.session.add(audit_log)
        return audit_log

    async def list_audit_logs(
        self,
        context: OrganizationContext,
        *,
        limit: int = 100,
    ) -> list[AuditLogResponse]:
        self._require_audit_read(context)
        statement = self._organization_statement(context).limit(limit)
        rows = (await self.session.scalars(statement)).all()
        return [self._response(row) for row in rows]

    async def get_audit_log(
        self,
        context: OrganizationContext,
        audit_log_id: UUID,
    ) -> AuditLogResponse:
        self._require_audit_read(context)
        statement = self._organization_statement(context).where(AuditLog.id == audit_log_id)
        audit_log = await self.session.scalar(statement)
        if audit_log is None:
            raise AuditLogNotFound(str(audit_log_id))
        return self._response(audit_log)

    async def export_audit_logs(
        self,
        context: OrganizationContext,
        *,
        export_format: str = "json",
        actor_ip: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        limit: int = 100,
    ) -> AuditLogExportResponse:
        rows = await self.list_audit_logs(context, limit=limit)
        await self.record_audit_log(
            AuditLogCreate(
                organization_id=context.organization_id,
                actor_type="user",
                actor_id=context.user_id,
                action="audit_logs.exported",
                resource_type="audit_log",
                resource_id=None,
                ip_address=actor_ip,
                user_agent=user_agent,
                request_id=request_id,
                metadata={"row_count": len(rows), "format": export_format},
            )
        )
        return AuditLogExportResponse(
            format="json",
            row_count=len(rows),
            rows=rows,
            exported_at=datetime.now(UTC),
        )

    def _organization_statement(self, context: OrganizationContext) -> Select[tuple[AuditLog]]:
        return (
            select(AuditLog)
            .where(AuditLog.organization_id == context.organization_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        )

    def _require_audit_read(self, context: OrganizationContext) -> None:
        if context.role not in AUDIT_READ_ROLES:
            raise AuditLogForbidden

    def _response(self, audit_log: AuditLog) -> AuditLogResponse:
        return AuditLogResponse(
            id=audit_log.id,
            organization_id=audit_log.organization_id,
            actor_type=audit_log.actor_type,
            actor_id=audit_log.actor_id,
            action=audit_log.action,
            resource_type=audit_log.resource_type,
            resource_id=audit_log.resource_id,
            ip_address=audit_log.ip_address,
            user_agent_hash=audit_log.user_agent_hash,
            request_id=audit_log.request_id,
            before=audit_log.before_json,
            after=audit_log.after_json,
            metadata=audit_log.metadata_json,
            created_at=audit_log.created_at,
        )


def redact_sensitive_values(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _redact_value(key, nested_value)
        for key, nested_value in value.items()
    }


def _redact_value(key: str, value: Any) -> Any:
    normalized_key = key.casefold()
    if any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
        return REDACTED
    if isinstance(value, dict):
        return redact_sensitive_values(value)
    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]
    return value


def _hash_user_agent(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    return hashlib.sha256(user_agent.encode("utf-8")).hexdigest()
