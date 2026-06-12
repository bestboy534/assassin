from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.transactions import transaction
from app.domains.files.models import StoredFile
from app.domains.organizations.models import OrganizationMember
from app.domains.organizations.service import OrganizationContext
from app.infrastructure.storage.base import ObjectStorage

from .control_schemas import (
    ComplianceControlResponse,
    ControlEvidenceResponse,
    ControlOwnerResponse,
    ControlReviewResponse,
    EvidenceDownloadResponse,
    FrameworkResponse,
    IncidentTaskResponse,
    SecurityIncidentResponse,
)
from .models import (
    ComplianceControl,
    ComplianceFramework,
    ControlEvidence,
    ControlOwner,
    ControlReview,
    IncidentTask,
    SecurityIncident,
)
from .service import AuditLogCreate, ComplianceService, _aware_utc

COMPLIANCE_ROLES = {"owner", "admin", "security", "security_admin", "auditor"}


class ComplianceAccessForbidden(Exception):
    pass


class ComplianceResourceNotFound(Exception):
    pass


class ComplianceResourceConflict(Exception):
    pass


@dataclass(frozen=True)
class CreateFramework:
    code: str
    name: str
    version: str
    description: str = ""


@dataclass(frozen=True)
class CreateControl:
    code: str
    title: str
    description: str = ""
    frequency_days: int = 90


@dataclass(frozen=True)
class CreateEvidence:
    stored_file_id: UUID
    title: str
    description: str = ""
    collected_at: datetime | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True)
class CreateIncident:
    title: str
    severity: str
    summary: str
    detected_at: datetime


@dataclass(frozen=True)
class CreateIncidentTask:
    title: str
    assignee_user_id: UUID | None = None
    due_at: datetime | None = None


class ComplianceControlService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_framework(
        self,
        context: OrganizationContext,
        body: CreateFramework,
    ) -> FrameworkResponse:
        self._require_access(context)
        framework = ComplianceFramework(
            organization_id=context.organization_id,
            created_by_user_id=context.user_id,
            code=body.code.strip().upper(),
            name=body.name.strip(),
            version=body.version.strip(),
            description=body.description.strip(),
            status="active",
        )
        async with transaction(self.session):
            self.session.add(framework)
        await self._audit(
            context,
            "compliance.framework.created",
            "compliance_framework",
            framework.id,
        )
        return self._framework_response(framework)

    async def list_frameworks(
        self,
        context: OrganizationContext,
    ) -> list[FrameworkResponse]:
        self._require_access(context)
        frameworks = (
            await self.session.scalars(
                select(ComplianceFramework)
                .where(ComplianceFramework.organization_id == context.organization_id)
                .order_by(ComplianceFramework.code.asc(), ComplianceFramework.version.asc())
            )
        ).all()
        return [self._framework_response(framework) for framework in frameworks]

    async def create_control(
        self,
        context: OrganizationContext,
        framework_id: UUID,
        body: CreateControl,
    ) -> ComplianceControlResponse:
        self._require_access(context)
        await self._framework(context, framework_id)
        control = ComplianceControl(
            organization_id=context.organization_id,
            framework_id=framework_id,
            code=body.code.strip().upper(),
            title=body.title.strip(),
            description=body.description.strip(),
            status="not_assessed",
            frequency_days=body.frequency_days,
        )
        async with transaction(self.session):
            self.session.add(control)
        await self._audit(
            context,
            "compliance.control.created",
            "compliance_control",
            control.id,
        )
        return await self.get_control(context, control.id)

    async def assign_owner(
        self,
        context: OrganizationContext,
        control_id: UUID,
        *,
        user_id: UUID,
        role: str,
    ) -> ControlOwnerResponse:
        self._require_access(context)
        await self._control(context, control_id)
        if not await self._active_member(context.organization_id, user_id):
            raise ComplianceResourceNotFound(str(user_id))
        owner = ControlOwner(
            organization_id=context.organization_id,
            control_id=control_id,
            user_id=user_id,
            role=role,
            assigned_by_user_id=context.user_id,
        )
        async with transaction(self.session):
            self.session.add(owner)
        await self._audit(
            context,
            "compliance.control_owner.assigned",
            "control_owner",
            owner.id,
        )
        return self._owner_response(owner)

    async def add_evidence(
        self,
        context: OrganizationContext,
        control_id: UUID,
        body: CreateEvidence,
    ) -> ControlEvidenceResponse:
        self._require_access(context)
        await self._control(context, control_id)
        stored_file = await self.session.scalar(
            select(StoredFile).where(
                StoredFile.id == body.stored_file_id,
                StoredFile.organization_id == context.organization_id,
                StoredFile.status == "available",
            )
        )
        if stored_file is None:
            raise ComplianceResourceNotFound(str(body.stored_file_id))
        now = datetime.now(UTC)
        expires_at = body.expires_at
        status = (
            "expired"
            if expires_at is not None and _aware_utc(expires_at) <= now
            else "active"
        )
        evidence = ControlEvidence(
            organization_id=context.organization_id,
            control_id=control_id,
            stored_file_id=body.stored_file_id,
            uploaded_by_user_id=context.user_id,
            title=body.title.strip(),
            description=body.description.strip(),
            status=status,
            collected_at=body.collected_at or now,
            expires_at=expires_at,
        )
        async with transaction(self.session):
            self.session.add(evidence)
        await self.refresh_control_status(context, control_id)
        await self._audit(
            context,
            "compliance.evidence.added",
            "control_evidence",
            evidence.id,
        )
        return self._evidence_response(evidence)

    async def create_review(
        self,
        context: OrganizationContext,
        control_id: UUID,
        *,
        outcome: str,
        notes: str,
    ) -> ControlReviewResponse:
        self._require_access(context)
        control = await self._control(context, control_id)
        now = datetime.now(UTC)
        review = ControlReview(
            organization_id=context.organization_id,
            control_id=control_id,
            reviewer_user_id=context.user_id,
            outcome=outcome,
            notes=notes.strip(),
            reviewed_at=now,
            next_review_at=now + timedelta(days=control.frequency_days),
        )
        async with transaction(self.session):
            self.session.add(review)
            control.last_reviewed_at = now
            control.next_review_at = review.next_review_at
        await self.refresh_control_status(context, control_id)
        await self._audit(
            context,
            "compliance.control.reviewed",
            "control_review",
            review.id,
        )
        return self._review_response(review)

    async def refresh_control_status(
        self,
        context: OrganizationContext,
        control_id: UUID,
    ) -> ComplianceControlResponse:
        self._require_access(context)
        control = await self._control(context, control_id)
        now = datetime.now(UTC)
        evidence = (
            await self.session.scalars(
                select(ControlEvidence).where(
                    ControlEvidence.organization_id == context.organization_id,
                    ControlEvidence.control_id == control_id,
                )
            )
        ).all()
        expired = False
        async with transaction(self.session):
            for item in evidence:
                item.status = (
                    "expired"
                    if item.expires_at is not None
                    and _aware_utc(item.expires_at) <= now
                    else "active"
                )
                expired = expired or item.status == "expired"
            latest_review = await self.session.scalar(
                select(ControlReview)
                .where(
                    ControlReview.organization_id == context.organization_id,
                    ControlReview.control_id == control_id,
                )
                .order_by(ControlReview.reviewed_at.desc(), ControlReview.id.desc())
            )
            if expired:
                control.status = "attention_required"
            elif latest_review is not None and latest_review.outcome == "effective" and evidence:
                control.status = "effective"
            elif latest_review is not None and latest_review.outcome != "effective":
                control.status = "attention_required"
            elif evidence:
                control.status = "in_progress"
            else:
                control.status = "not_assessed"
        return await self.get_control(context, control_id)

    async def get_control(
        self,
        context: OrganizationContext,
        control_id: UUID,
    ) -> ComplianceControlResponse:
        self._require_access(context)
        control = await self.session.scalar(
            select(ComplianceControl)
            .options(
                selectinload(ComplianceControl.owners),
                selectinload(ComplianceControl.evidence),
                selectinload(ComplianceControl.reviews),
            )
            .where(
                ComplianceControl.id == control_id,
                ComplianceControl.organization_id == context.organization_id,
            )
        )
        if control is None:
            raise ComplianceResourceNotFound(str(control_id))
        return self._control_response(control)

    async def create_evidence_download(
        self,
        context: OrganizationContext,
        evidence_id: UUID,
        *,
        storage: ObjectStorage,
        expires_in: int,
    ) -> EvidenceDownloadResponse:
        self._require_access(context)
        row = (
            await self.session.execute(
                select(ControlEvidence, StoredFile)
                .join(StoredFile, StoredFile.id == ControlEvidence.stored_file_id)
                .where(
                    ControlEvidence.id == evidence_id,
                    ControlEvidence.organization_id == context.organization_id,
                    StoredFile.organization_id == context.organization_id,
                    StoredFile.status == "available",
                )
            )
        ).first()
        if row is None:
            raise ComplianceResourceNotFound(str(evidence_id))
        _, stored_file = row
        if stored_file.storage_key is None:
            raise ComplianceResourceConflict("Evidence file is not available")
        download_url = storage.presign_download(stored_file.storage_key, expires_in)
        await self._audit(
            context,
            "compliance.evidence.downloaded",
            "control_evidence",
            evidence_id,
        )
        return EvidenceDownloadResponse(
            id=evidence_id,
            download_url=download_url,
            expires_in=expires_in,
        )

    async def _framework(
        self,
        context: OrganizationContext,
        framework_id: UUID,
    ) -> ComplianceFramework:
        framework = await self.session.scalar(
            select(ComplianceFramework).where(
                ComplianceFramework.id == framework_id,
                ComplianceFramework.organization_id == context.organization_id,
            )
        )
        if framework is None:
            raise ComplianceResourceNotFound(str(framework_id))
        return framework

    async def _control(
        self,
        context: OrganizationContext,
        control_id: UUID,
    ) -> ComplianceControl:
        control = await self.session.scalar(
            select(ComplianceControl).where(
                ComplianceControl.id == control_id,
                ComplianceControl.organization_id == context.organization_id,
            )
        )
        if control is None:
            raise ComplianceResourceNotFound(str(control_id))
        return control

    async def _active_member(self, organization_id: UUID, user_id: UUID) -> bool:
        return (
            await self.session.scalar(
                select(OrganizationMember.id).where(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.status == "active",
                )
            )
        ) is not None

    async def _audit(
        self,
        context: OrganizationContext,
        action: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        await ComplianceService(self.session).record_audit_log(
            AuditLogCreate(
                organization_id=context.organization_id,
                actor_type="user",
                actor_id=context.user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
            )
        )

    def _require_access(self, context: OrganizationContext) -> None:
        if context.role not in COMPLIANCE_ROLES:
            raise ComplianceAccessForbidden

    def _framework_response(self, framework: ComplianceFramework) -> FrameworkResponse:
        return FrameworkResponse(
            id=framework.id,
            organization_id=framework.organization_id,
            code=framework.code,
            name=framework.name,
            version=framework.version,
            description=framework.description,
            status=framework.status,
            created_at=framework.created_at,
            updated_at=framework.updated_at,
        )

    def _owner_response(self, owner: ControlOwner) -> ControlOwnerResponse:
        return ControlOwnerResponse(
            id=owner.id,
            user_id=owner.user_id,
            role=owner.role,
            created_at=owner.created_at,
        )

    def _evidence_response(self, evidence: ControlEvidence) -> ControlEvidenceResponse:
        return ControlEvidenceResponse(
            id=evidence.id,
            stored_file_id=evidence.stored_file_id,
            title=evidence.title,
            description=evidence.description,
            status=evidence.status,
            collected_at=evidence.collected_at,
            expires_at=evidence.expires_at,
            created_at=evidence.created_at,
        )

    def _review_response(self, review: ControlReview) -> ControlReviewResponse:
        return ControlReviewResponse(
            id=review.id,
            reviewer_user_id=review.reviewer_user_id,
            outcome=review.outcome,
            notes=review.notes,
            reviewed_at=review.reviewed_at,
            next_review_at=review.next_review_at,
            created_at=review.created_at,
        )

    def _control_response(self, control: ComplianceControl) -> ComplianceControlResponse:
        return ComplianceControlResponse(
            id=control.id,
            organization_id=control.organization_id,
            framework_id=control.framework_id,
            code=control.code,
            title=control.title,
            description=control.description,
            status=control.status,
            frequency_days=control.frequency_days,
            last_reviewed_at=control.last_reviewed_at,
            next_review_at=control.next_review_at,
            owners=[self._owner_response(owner) for owner in control.owners],
            evidence=[self._evidence_response(item) for item in control.evidence],
            reviews=[self._review_response(review) for review in control.reviews],
            created_at=control.created_at,
            updated_at=control.updated_at,
        )


class SecurityIncidentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_incident(
        self,
        context: OrganizationContext,
        body: CreateIncident,
    ) -> SecurityIncidentResponse:
        self._require_access(context)
        incident = SecurityIncident(
            organization_id=context.organization_id,
            created_by_user_id=context.user_id,
            title=body.title.strip(),
            severity=body.severity,
            status="open",
            summary=body.summary.strip(),
            detected_at=body.detected_at,
        )
        async with transaction(self.session):
            self.session.add(incident)
        await self._audit(context, "security.incident.created", "security_incident", incident.id)
        return await self.get_incident(context, incident.id)

    async def list_incidents(
        self,
        context: OrganizationContext,
    ) -> list[SecurityIncidentResponse]:
        self._require_access(context)
        incidents = (
            await self.session.scalars(
                select(SecurityIncident)
                .options(selectinload(SecurityIncident.tasks))
                .where(SecurityIncident.organization_id == context.organization_id)
                .order_by(SecurityIncident.detected_at.desc(), SecurityIncident.id.desc())
            )
        ).all()
        return [self._incident_response(incident) for incident in incidents]

    async def get_incident(
        self,
        context: OrganizationContext,
        incident_id: UUID,
    ) -> SecurityIncidentResponse:
        self._require_access(context)
        incident = await self.session.scalar(
            select(SecurityIncident)
            .options(selectinload(SecurityIncident.tasks))
            .where(
                SecurityIncident.id == incident_id,
                SecurityIncident.organization_id == context.organization_id,
            )
        )
        if incident is None:
            raise ComplianceResourceNotFound(str(incident_id))
        return self._incident_response(incident)

    async def add_task(
        self,
        context: OrganizationContext,
        incident_id: UUID,
        body: CreateIncidentTask,
    ) -> IncidentTaskResponse:
        self._require_access(context)
        await self._incident(context, incident_id)
        if body.assignee_user_id is not None and not await self._active_member(
            context.organization_id,
            body.assignee_user_id,
        ):
            raise ComplianceResourceNotFound(str(body.assignee_user_id))
        task = IncidentTask(
            organization_id=context.organization_id,
            incident_id=incident_id,
            title=body.title.strip(),
            status="open",
            assignee_user_id=body.assignee_user_id,
            due_at=body.due_at,
        )
        async with transaction(self.session):
            self.session.add(task)
        await self._audit(context, "security.incident_task.created", "incident_task", task.id)
        return self._task_response(task)

    async def update_task(
        self,
        context: OrganizationContext,
        incident_id: UUID,
        task_id: UUID,
        *,
        status: str,
    ) -> IncidentTaskResponse:
        self._require_access(context)
        await self._incident(context, incident_id)
        task = await self.session.scalar(
            select(IncidentTask).where(
                IncidentTask.id == task_id,
                IncidentTask.incident_id == incident_id,
                IncidentTask.organization_id == context.organization_id,
            )
        )
        if task is None:
            raise ComplianceResourceNotFound(str(task_id))
        async with transaction(self.session):
            task.status = status
            task.completed_at = datetime.now(UTC) if status == "completed" else None
        await self._audit(context, "security.incident_task.updated", "incident_task", task.id)
        await self.session.refresh(task)
        return self._task_response(task)

    async def _incident(
        self,
        context: OrganizationContext,
        incident_id: UUID,
    ) -> SecurityIncident:
        incident = await self.session.scalar(
            select(SecurityIncident).where(
                SecurityIncident.id == incident_id,
                SecurityIncident.organization_id == context.organization_id,
            )
        )
        if incident is None:
            raise ComplianceResourceNotFound(str(incident_id))
        return incident

    async def _active_member(self, organization_id: UUID, user_id: UUID) -> bool:
        return (
            await self.session.scalar(
                select(OrganizationMember.id).where(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.status == "active",
                )
            )
        ) is not None

    async def _audit(
        self,
        context: OrganizationContext,
        action: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        await ComplianceService(self.session).record_audit_log(
            AuditLogCreate(
                organization_id=context.organization_id,
                actor_type="user",
                actor_id=context.user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
            )
        )

    def _require_access(self, context: OrganizationContext) -> None:
        if context.role not in COMPLIANCE_ROLES:
            raise ComplianceAccessForbidden

    def _task_response(self, task: IncidentTask) -> IncidentTaskResponse:
        return IncidentTaskResponse(
            id=task.id,
            title=task.title,
            status=task.status,
            assignee_user_id=task.assignee_user_id,
            due_at=task.due_at,
            completed_at=task.completed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    def _incident_response(self, incident: SecurityIncident) -> SecurityIncidentResponse:
        return SecurityIncidentResponse(
            id=incident.id,
            organization_id=incident.organization_id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            summary=incident.summary,
            detected_at=incident.detected_at,
            resolved_at=incident.resolved_at,
            tasks=[self._task_response(task) for task in incident.tasks],
            created_at=incident.created_at,
            updated_at=incident.updated_at,
        )
