import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.files.models import StoredFile
from app.domains.organizations.service import OrganizationContext
from app.infrastructure.storage.base import ObjectStorage

from .models import AuditLog, DeletionJob, DeletionJobItem, LegalHold, RetentionPolicy
from .schemas import (
    AuditLogExportResponse,
    AuditLogResponse,
    DeletionJobResponse,
    DeletionPreviewResponse,
    LegalHoldResponse,
    RetentionPolicyResponse,
)

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


class RetentionForbidden(Exception):
    pass


class RetentionPolicyNotFound(Exception):
    pass


class ReauthenticationRequired(Exception):
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


@dataclass(frozen=True)
class CreateRetentionPolicy:
    data_type: str
    retention_days: int
    description: str = ""


@dataclass(frozen=True)
class CreateLegalHold:
    resource_type: str
    resource_id: str
    reason: str
    expires_at: datetime | None = None


@dataclass(frozen=True)
class RetentionDeletionResult:
    id: UUID
    data_type: str
    status: str
    deleted_resource_ids: list[str]
    skipped_legal_hold: list[str]
    created_at: datetime
    completed_at: datetime | None


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


class RetentionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: ObjectStorage | None = None,
    ) -> None:
        self.session = session
        self.storage = storage

    async def create_policy(
        self,
        *,
        organization_id: UUID,
        created_by_user_id: UUID,
        body: CreateRetentionPolicy,
    ) -> RetentionPolicyResponse:
        policy = RetentionPolicy(
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            data_type=body.data_type,
            retention_days=body.retention_days,
            action="delete",
            description=body.description,
            status="active",
        )
        async with transaction(self.session):
            self.session.add(policy)
        await ComplianceService(self.session).record_audit_log(
            AuditLogCreate(
                organization_id=organization_id,
                actor_type="user",
                actor_id=created_by_user_id,
                action="retention.policy.created",
                resource_type="retention_policy",
                resource_id=str(policy.id),
                after={
                    "data_type": policy.data_type,
                    "retention_days": policy.retention_days,
                    "status": policy.status,
                },
            )
        )
        return self._policy_response(policy)

    async def create_legal_hold(
        self,
        *,
        organization_id: UUID,
        created_by_user_id: UUID,
        body: CreateLegalHold,
    ) -> LegalHoldResponse:
        legal_hold = LegalHold(
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            resource_type=body.resource_type,
            resource_id=body.resource_id,
            reason=body.reason,
            status="active",
            expires_at=body.expires_at,
        )
        async with transaction(self.session):
            self.session.add(legal_hold)
        await ComplianceService(self.session).record_audit_log(
            AuditLogCreate(
                organization_id=organization_id,
                actor_type="user",
                actor_id=created_by_user_id,
                action="legal_hold.created",
                resource_type=body.resource_type,
                resource_id=body.resource_id,
                metadata={"reason": body.reason},
            )
        )
        return self._legal_hold_response(legal_hold)

    async def preview_expired(
        self,
        *,
        organization_id: UUID,
        data_type: str = "stored_file",
    ) -> DeletionPreviewResponse:
        policy = await self._active_policy(organization_id, data_type)
        cutoff_at = datetime.now(UTC) - timedelta(days=policy.retention_days)
        files = await self._expired_stored_files(organization_id, cutoff_at)
        legal_hold_ids = await self._active_legal_hold_resource_ids(
            organization_id,
            "stored_file",
        )
        delete_candidates: list[str] = []
        skipped_legal_hold: list[str] = []
        for stored_file in files:
            resource_id = str(stored_file.id)
            if resource_id in legal_hold_ids:
                skipped_legal_hold.append(resource_id)
            else:
                delete_candidates.append(resource_id)
        return DeletionPreviewResponse(
            data_type=data_type,
            cutoff_at=cutoff_at,
            delete_candidates=delete_candidates,
            skipped_legal_hold=skipped_legal_hold,
        )

    async def delete_expired(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        data_type: str = "stored_file",
        reauth_confirmed: bool,
    ) -> RetentionDeletionResult:
        if not reauth_confirmed:
            raise ReauthenticationRequired
        policy = await self._active_policy(organization_id, data_type)
        cutoff_at = datetime.now(UTC) - timedelta(days=policy.retention_days)
        files = await self._expired_stored_files(organization_id, cutoff_at)
        legal_hold_ids = await self._active_legal_hold_resource_ids(
            organization_id,
            "stored_file",
        )
        now = datetime.now(UTC)
        deleted_resource_ids: list[str] = []
        skipped_legal_hold: list[str] = []
        job = DeletionJob(
            organization_id=organization_id,
            requested_by_user_id=actor_user_id,
            data_type=data_type,
            status="running",
            reauth_confirmed_at=now,
            summary_json={},
        )
        async with transaction(self.session):
            self.session.add(job)
            await self.session.flush()
            for stored_file in files:
                resource_id = str(stored_file.id)
                if resource_id in legal_hold_ids:
                    skipped_legal_hold.append(resource_id)
                    self.session.add(
                        DeletionJobItem(
                            organization_id=organization_id,
                            deletion_job_id=job.id,
                            resource_type="stored_file",
                            resource_id=resource_id,
                            action="skip",
                            status="skipped",
                            reason="legal_hold",
                            metadata_json={"filename": stored_file.filename},
                        )
                    )
                    continue
                self._delete_storage_object(stored_file)
                stored_file.status = "deleted"
                deleted_resource_ids.append(resource_id)
                self.session.add(
                    DeletionJobItem(
                        organization_id=organization_id,
                        deletion_job_id=job.id,
                        resource_type="stored_file",
                        resource_id=resource_id,
                        action="delete",
                        status="deleted",
                        reason=None,
                        metadata_json={
                            "filename": stored_file.filename,
                            "storage_key": stored_file.storage_key,
                        },
                    )
                )
            job.status = "succeeded"
            job.completed_at = datetime.now(UTC)
            job.summary_json = {
                "deleted_resource_ids": deleted_resource_ids,
                "skipped_legal_hold": skipped_legal_hold,
            }
        await ComplianceService(self.session).record_audit_log(
            AuditLogCreate(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_user_id,
                action="retention.deletion_job.completed",
                resource_type="deletion_job",
                resource_id=str(job.id),
                metadata=job.summary_json,
            )
        )
        return RetentionDeletionResult(
            id=job.id,
            data_type=job.data_type,
            status=job.status,
            deleted_resource_ids=deleted_resource_ids,
            skipped_legal_hold=skipped_legal_hold,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )

    async def _active_policy(self, organization_id: UUID, data_type: str) -> RetentionPolicy:
        policy = await self.session.scalar(
            select(RetentionPolicy)
            .where(
                RetentionPolicy.organization_id == organization_id,
                RetentionPolicy.data_type == data_type,
                RetentionPolicy.status == "active",
            )
            .order_by(RetentionPolicy.created_at.desc(), RetentionPolicy.id.desc())
        )
        if policy is None:
            raise RetentionPolicyNotFound(data_type)
        return policy

    async def _expired_stored_files(
        self,
        organization_id: UUID,
        cutoff_at: datetime,
    ) -> list[StoredFile]:
        return list(
            (
                await self.session.scalars(
                    select(StoredFile)
                    .where(
                        StoredFile.organization_id == organization_id,
                        StoredFile.status != "deleted",
                        StoredFile.created_at <= cutoff_at,
                    )
                    .order_by(StoredFile.created_at.asc(), StoredFile.id.asc())
                )
            ).all()
        )

    async def _active_legal_hold_resource_ids(
        self,
        organization_id: UUID,
        resource_type: str,
    ) -> set[str]:
        now = datetime.now(UTC)
        holds = (
            await self.session.scalars(
                select(LegalHold).where(
                    LegalHold.organization_id == organization_id,
                    LegalHold.resource_type == resource_type,
                    LegalHold.status == "active",
                )
            )
        ).all()
        return {
            hold.resource_id
            for hold in holds
            if hold.expires_at is None or _aware_utc(hold.expires_at) > now
        }

    def _delete_storage_object(self, stored_file: StoredFile) -> None:
        if self.storage is None:
            return
        key = stored_file.storage_key or stored_file.quarantine_key
        self.storage.delete(key)

    def _policy_response(self, policy: RetentionPolicy) -> RetentionPolicyResponse:
        return RetentionPolicyResponse(
            id=policy.id,
            organization_id=policy.organization_id,
            data_type=policy.data_type,
            retention_days=policy.retention_days,
            action=policy.action,
            description=policy.description,
            status=policy.status,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )

    def _legal_hold_response(self, legal_hold: LegalHold) -> LegalHoldResponse:
        return LegalHoldResponse(
            id=legal_hold.id,
            organization_id=legal_hold.organization_id,
            resource_type=legal_hold.resource_type,
            resource_id=legal_hold.resource_id,
            reason=legal_hold.reason,
            status=legal_hold.status,
            expires_at=legal_hold.expires_at,
            created_at=legal_hold.created_at,
        )


def deletion_result_response(result: RetentionDeletionResult) -> DeletionJobResponse:
    return DeletionJobResponse(
        id=result.id,
        data_type=result.data_type,
        status=result.status,
        deleted_resource_ids=result.deleted_resource_ids,
        skipped_legal_hold=result.skipped_legal_hold,
        created_at=result.created_at,
        completed_at=result.completed_at,
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
