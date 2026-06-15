from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.billing.service import EntitlementService
from app.domains.compliance.service import AuditLogCreate, ComplianceService
from app.domains.identity.models import User
from app.domains.integrations.models import SyncRun
from app.domains.organizations.models import OrganizationMember
from app.domains.organizations.service import OrganizationContext
from app.domains.outbox.models import OutboxEvent
from app.domains.outbox.repository import OutboxRepository

from .models import (
    SupportAccessLog,
    SupportGrant,
    SupportMessage,
    SupportSatisfaction,
    SupportSlaEvent,
    SupportTicket,
)
from .schemas import (
    CreateSupportGrantRequest,
    CreateSupportSatisfactionRequest,
    CreateSupportTicketRequest,
    SupportDiagnosticResponse,
    SupportGrantListResponse,
    SupportGrantResponse,
    SupportMessageListResponse,
    SupportMessageResponse,
    SupportSatisfactionResponse,
    SupportTicketListResponse,
    SupportTicketResponse,
    SyncDiagnosticItem,
)

SUPPORT_TICKET_STATUSES = {
    "new",
    "open",
    "waiting_customer",
    "waiting_support",
    "resolved",
    "closed",
}
SUPPORT_SCOPES = {
    "configuration.read",
    "sync_diagnostics.read",
    "job_logs.read",
    "business_records.read",
}
GRANT_MANAGEMENT_ROLES = {"owner", "admin"}


class SupportTicketNotFound(Exception):
    pass


class SupportPermissionDenied(Exception):
    pass


class InvalidSupportOperation(Exception):
    pass


class SupportTicketService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.outbox = OutboxRepository(session)

    async def create(
        self,
        context: OrganizationContext,
        user: User,
        body: CreateSupportTicketRequest,
        *,
        now: datetime | None = None,
    ) -> SupportTicketResponse:
        current_time = self._as_utc(now or datetime.now(UTC))
        entitlement = await EntitlementService(self.session).resolve(
            context.organization_id,
            "support_tier",
        )
        support_tier = (
            str(entitlement.value)
            if entitlement.value_type == "support_tier"
            else "standard"
        )
        first_hours, resolution_hours = self._sla_hours(support_tier, body.priority)
        ticket = SupportTicket(
            organization_id=context.organization_id,
            created_by_user_id=user.id,
            subject=body.subject.strip(),
            description=body.description.strip(),
            category=body.category.strip().lower(),
            priority=body.priority,
            status="new",
            support_tier=support_tier,
            first_response_due_at=current_time + timedelta(hours=first_hours),
            resolution_due_at=current_time + timedelta(hours=resolution_hours),
        )
        async with transaction(self.session):
            self.session.add(ticket)
            await self.session.flush()
            self.session.add_all(
                [
                    SupportSlaEvent(
                        organization_id=context.organization_id,
                        support_ticket_id=ticket.id,
                        event_type="first_response_target",
                        target_at=ticket.first_response_due_at,
                    ),
                    SupportSlaEvent(
                        organization_id=context.organization_id,
                        support_ticket_id=ticket.id,
                        event_type="resolution_target",
                        target_at=ticket.resolution_due_at,
                    ),
                ]
            )
            await ComplianceService(self.session).record_audit_log(
                AuditLogCreate(
                    organization_id=context.organization_id,
                    actor_type="user",
                    actor_id=user.id,
                    action="support.ticket_created",
                    resource_type="support_ticket",
                    resource_id=str(ticket.id),
                    after={"subject": ticket.subject, "priority": ticket.priority},
                )
            )
        return self.ticket_response(ticket)

    async def list(
        self,
        context: OrganizationContext,
    ) -> SupportTicketListResponse:
        tickets = list(
            (
                await self.session.scalars(
                    select(SupportTicket)
                    .where(SupportTicket.organization_id == context.organization_id)
                    .order_by(SupportTicket.created_at.desc())
                )
            ).all()
        )
        return SupportTicketListResponse(
            items=[self.ticket_response(ticket) for ticket in tickets]
        )

    async def get_for_user(
        self,
        ticket_id: UUID,
        user_id: UUID,
    ) -> SupportTicket:
        ticket = await self.session.scalar(
            select(SupportTicket)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == SupportTicket.organization_id,
            )
            .where(
                SupportTicket.id == ticket_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "active",
            )
        )
        if ticket is None:
            raise SupportTicketNotFound
        return ticket

    async def get_for_operator(self, ticket_id: UUID) -> SupportTicket:
        ticket = await self.session.get(SupportTicket, ticket_id)
        if ticket is None:
            raise SupportTicketNotFound
        return ticket

    async def list_for_operator(self) -> SupportTicketListResponse:
        tickets = list(
            (
                await self.session.scalars(
                    select(SupportTicket).order_by(SupportTicket.created_at.desc())
                )
            ).all()
        )
        return SupportTicketListResponse(
            items=[self.ticket_response(ticket) for ticket in tickets]
        )

    async def messages(
        self,
        ticket: SupportTicket,
        *,
        include_internal: bool,
    ) -> SupportMessageListResponse:
        statement = (
            select(SupportMessage)
            .where(SupportMessage.support_ticket_id == ticket.id)
            .order_by(SupportMessage.created_at, SupportMessage.id)
        )
        if not include_internal:
            statement = statement.where(SupportMessage.internal.is_(False))
        messages = list((await self.session.scalars(statement)).all())
        return SupportMessageListResponse(
            items=[self.message_response(message) for message in messages]
        )

    async def add_customer_message(
        self,
        ticket: SupportTicket,
        user: User,
        body: str,
    ) -> SupportMessageResponse:
        if ticket.status in {"resolved", "closed"}:
            raise InvalidSupportOperation("Resolved ticket cannot receive new messages")
        current_time = datetime.now(UTC)
        message = SupportMessage(
            organization_id=ticket.organization_id,
            support_ticket_id=ticket.id,
            author_user_id=user.id,
            author_type="customer",
            body=body.strip(),
            internal=False,
            created_at=current_time,
        )
        async with transaction(self.session):
            self.session.add(message)
            if ticket.status in {"new", "waiting_customer"}:
                self._resume_sla(ticket)
                ticket.status = "waiting_support"
                ticket.updated_at = current_time
            await self.session.flush()
        return self.message_response(message)

    async def add_support_message(
        self,
        ticket: SupportTicket,
        user: User,
        body: str,
    ) -> SupportMessageResponse:
        if ticket.status in {"resolved", "closed"}:
            raise InvalidSupportOperation("Resolved ticket cannot receive new messages")
        current_time = datetime.now(UTC)
        message = SupportMessage(
            organization_id=ticket.organization_id,
            support_ticket_id=ticket.id,
            author_user_id=user.id,
            author_type="support",
            body=body.strip(),
            internal=False,
            created_at=current_time,
        )
        async with transaction(self.session):
            self.session.add(message)
            if ticket.first_responded_at is None:
                ticket.first_responded_at = current_time
            ticket.status = "waiting_customer"
            ticket.sla_paused_at = ticket.sla_paused_at or current_time
            ticket.updated_at = current_time
            await self.session.flush()
            await ComplianceService(self.session).record_audit_log(
                AuditLogCreate(
                    organization_id=ticket.organization_id,
                    actor_type="support_user",
                    actor_id=user.id,
                    action="support.message_created",
                    resource_type="support_ticket",
                    resource_id=str(ticket.id),
                )
            )
            await self.outbox.add(
                "support.message_created",
                message.id,
                {
                    "ticket_id": str(ticket.id),
                    "organization_id": str(ticket.organization_id),
                    "message_id": str(message.id),
                },
                organization_id=ticket.organization_id,
            )
        return self.message_response(message)

    async def update_status(
        self,
        ticket: SupportTicket,
        status: str,
    ) -> SupportTicketResponse:
        if status not in SUPPORT_TICKET_STATUSES:
            raise InvalidSupportOperation("Unsupported support ticket status")
        current_time = datetime.now(UTC)
        async with transaction(self.session):
            if status == "waiting_customer" and ticket.sla_paused_at is None:
                ticket.sla_paused_at = current_time
            elif status != "waiting_customer":
                self._resume_sla(ticket, now=current_time)
            ticket.status = status
            ticket.updated_at = current_time
            if status == "closed":
                ticket.closed_at = current_time
        return self.ticket_response(ticket)

    async def resolve(
        self,
        ticket: SupportTicket,
        resolution: str,
        user: User,
    ) -> SupportTicketResponse:
        current_time = datetime.now(UTC)
        async with transaction(self.session):
            self._resume_sla(ticket, now=current_time)
            ticket.status = "resolved"
            ticket.resolution_summary = resolution.strip()
            ticket.resolved_at = current_time
            ticket.updated_at = current_time
            self.session.add(
                SupportSlaEvent(
                    organization_id=ticket.organization_id,
                    support_ticket_id=ticket.id,
                    event_type="resolved",
                    target_at=ticket.resolution_due_at,
                    metadata_json={
                        "within_sla": current_time <= self._as_utc(
                            ticket.resolution_due_at
                        )
                    },
                )
            )
            await ComplianceService(self.session).record_audit_log(
                AuditLogCreate(
                    organization_id=ticket.organization_id,
                    actor_type="user",
                    actor_id=user.id,
                    action="support.ticket_resolved",
                    resource_type="support_ticket",
                    resource_id=str(ticket.id),
                )
            )
        return self.ticket_response(ticket)

    async def submit_satisfaction(
        self,
        ticket: SupportTicket,
        user: User,
        body: CreateSupportSatisfactionRequest,
    ) -> SupportSatisfactionResponse:
        if ticket.status not in {"resolved", "closed"}:
            raise InvalidSupportOperation("Only resolved tickets can be rated")
        satisfaction = SupportSatisfaction(
            organization_id=ticket.organization_id,
            support_ticket_id=ticket.id,
            submitted_by_user_id=user.id,
            rating=body.rating,
            comment=body.comment.strip(),
        )
        try:
            async with transaction(self.session):
                self.session.add(satisfaction)
                await self.session.flush()
        except IntegrityError as exc:
            raise InvalidSupportOperation("Ticket satisfaction already submitted") from exc
        return SupportSatisfactionResponse(
            id=satisfaction.id,
            support_ticket_id=satisfaction.support_ticket_id,
            rating=satisfaction.rating,
            comment=satisfaction.comment,
            created_at=satisfaction.created_at,
        )

    async def queue_sla_warnings(
        self,
        *,
        now: datetime | None = None,
    ) -> int:
        current_time = self._as_utc(now or datetime.now(UTC))
        warning_limit = current_time + timedelta(hours=1)
        tickets = list(
            (
                await self.session.scalars(
                    select(SupportTicket).where(
                        SupportTicket.status.not_in({"resolved", "closed", "waiting_customer"}),
                        SupportTicket.resolution_due_at > current_time,
                        SupportTicket.resolution_due_at <= warning_limit,
                    )
                )
            ).all()
        )
        queued = 0
        async with transaction(self.session):
            for ticket in tickets:
                aggregate_id = f"{ticket.id}:resolution"
                existing = await self.session.scalar(
                    select(OutboxEvent.id).where(
                        OutboxEvent.event_type == "support.sla_warning",
                        OutboxEvent.aggregate_id == aggregate_id,
                    )
                )
                if existing is not None:
                    continue
                await self.outbox.add(
                    "support.sla_warning",
                    aggregate_id,
                    {
                        "ticket_id": str(ticket.id),
                        "organization_id": str(ticket.organization_id),
                        "target_at": self._as_utc(
                            ticket.resolution_due_at
                        ).isoformat(),
                    },
                    organization_id=ticket.organization_id,
                )
                queued += 1
        return queued

    @staticmethod
    def ticket_response(ticket: SupportTicket) -> SupportTicketResponse:
        return SupportTicketResponse(
            id=ticket.id,
            organization_id=ticket.organization_id,
            subject=ticket.subject,
            description=ticket.description,
            category=ticket.category,
            priority=ticket.priority,
            status=ticket.status,
            support_tier=ticket.support_tier,
            resolution_summary=ticket.resolution_summary,
            first_response_due_at=ticket.first_response_due_at,
            resolution_due_at=ticket.resolution_due_at,
            first_responded_at=ticket.first_responded_at,
            sla_paused_at=ticket.sla_paused_at,
            resolved_at=ticket.resolved_at,
            closed_at=ticket.closed_at,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )

    @staticmethod
    def message_response(message: SupportMessage) -> SupportMessageResponse:
        return SupportMessageResponse(
            id=message.id,
            support_ticket_id=message.support_ticket_id,
            author_type=message.author_type,
            body=message.body,
            internal=message.internal,
            created_at=message.created_at,
        )

    @staticmethod
    def _sla_hours(support_tier: str, priority: str) -> tuple[int, int]:
        first, resolution = (4, 24) if support_tier == "priority" else (24, 72)
        if priority == "urgent":
            return max(first // 2, 1), max(resolution // 2, 4)
        if priority == "low":
            return first * 2, resolution * 2
        return first, resolution

    @staticmethod
    def _resume_sla(
        ticket: SupportTicket,
        *,
        now: datetime | None = None,
    ) -> None:
        if ticket.sla_paused_at is None:
            return
        current_time = now or datetime.now(UTC)
        paused_at = SupportTicketService._as_utc(ticket.sla_paused_at)
        pause_seconds = max(int((current_time - paused_at).total_seconds()), 0)
        ticket.sla_paused_seconds += pause_seconds
        ticket.first_response_due_at = (
            SupportTicketService._as_utc(ticket.first_response_due_at)
            + timedelta(seconds=pause_seconds)
        )
        ticket.resolution_due_at = (
            SupportTicketService._as_utc(ticket.resolution_due_at)
            + timedelta(seconds=pause_seconds)
        )
        ticket.sla_paused_at = None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class SupportGrantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        context: OrganizationContext,
        body: CreateSupportGrantRequest,
    ) -> SupportGrantResponse:
        self._require_manager(context)
        scopes = list(dict.fromkeys(body.scopes))
        unsupported = set(scopes) - SUPPORT_SCOPES
        if unsupported:
            raise InvalidSupportOperation(
                f"Unsupported support scopes: {', '.join(sorted(unsupported))}"
            )
        expires_at = SupportTicketService._as_utc(body.expires_at)
        now = datetime.now(UTC)
        if expires_at <= now or expires_at > now + timedelta(days=7):
            raise InvalidSupportOperation(
                "Support grant must expire within the next 7 days"
            )
        grant = SupportGrant(
            organization_id=context.organization_id,
            support_user_id=body.support_user_id,
            scopes_json=scopes,
            reason=body.reason.strip(),
            approved_by_user_id=context.user_id,
            expires_at=expires_at,
        )
        async with transaction(self.session):
            self.session.add(grant)
            await self.session.flush()
            await ComplianceService(self.session).record_audit_log(
                AuditLogCreate(
                    organization_id=context.organization_id,
                    actor_type="user",
                    actor_id=context.user_id,
                    action="support.grant_created",
                    resource_type="support_grant",
                    resource_id=str(grant.id),
                    after={
                        "support_user_id": str(grant.support_user_id),
                        "scopes": scopes,
                        "reason": grant.reason,
                        "expires_at": expires_at.isoformat(),
                    },
                )
            )
        return self.response(grant)

    async def list(
        self,
        context: OrganizationContext,
    ) -> SupportGrantListResponse:
        self._require_manager(context)
        grants = list(
            (
                await self.session.scalars(
                    select(SupportGrant)
                    .where(SupportGrant.organization_id == context.organization_id)
                    .order_by(SupportGrant.created_at.desc())
                )
            ).all()
        )
        return SupportGrantListResponse(items=[self.response(grant) for grant in grants])

    async def revoke(
        self,
        context: OrganizationContext,
        grant_id: UUID,
    ) -> SupportGrantResponse:
        self._require_manager(context)
        grant = await self.session.scalar(
            select(SupportGrant).where(
                SupportGrant.id == grant_id,
                SupportGrant.organization_id == context.organization_id,
            )
        )
        if grant is None:
            raise SupportTicketNotFound
        async with transaction(self.session):
            grant.revoked_at = datetime.now(UTC)
            await ComplianceService(self.session).record_audit_log(
                AuditLogCreate(
                    organization_id=context.organization_id,
                    actor_type="user",
                    actor_id=context.user_id,
                    action="support.grant_revoked",
                    resource_type="support_grant",
                    resource_id=str(grant.id),
                )
            )
        return self.response(grant)

    @staticmethod
    def response(grant: SupportGrant) -> SupportGrantResponse:
        return SupportGrantResponse(
            id=grant.id,
            organization_id=grant.organization_id,
            support_user_id=grant.support_user_id,
            scopes=list(grant.scopes_json),
            reason=grant.reason,
            approved_by_user_id=grant.approved_by_user_id,
            expires_at=grant.expires_at,
            revoked_at=grant.revoked_at,
            created_at=grant.created_at,
        )

    @staticmethod
    def _require_manager(context: OrganizationContext) -> None:
        if context.role not in GRANT_MANAGEMENT_ROLES:
            raise SupportPermissionDenied


class SupportAccessService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def read_sync_diagnostics(
        self,
        grant_id: UUID,
        *,
        support_user_id: UUID,
        purpose: str,
        now: datetime | None = None,
    ) -> SupportDiagnosticResponse:
        grant = await self.session.get(SupportGrant, grant_id)
        current_time = SupportTicketService._as_utc(now or datetime.now(UTC))
        if (
            grant is None
            or grant.support_user_id != support_user_id
            or grant.revoked_at is not None
            or SupportTicketService._as_utc(grant.expires_at) <= current_time
            or "sync_diagnostics.read" not in grant.scopes_json
        ):
            raise SupportPermissionDenied
        normalized_purpose = purpose.strip()
        if not normalized_purpose:
            raise InvalidSupportOperation("Diagnostic access purpose is required")
        runs = list(
            (
                await self.session.scalars(
                    select(SyncRun)
                    .where(SyncRun.organization_id == grant.organization_id)
                    .order_by(SyncRun.started_at.desc())
                    .limit(20)
                )
            ).all()
        )
        async with transaction(self.session):
            self.session.add(
                SupportAccessLog(
                    organization_id=grant.organization_id,
                    support_grant_id=grant.id,
                    support_user_id=support_user_id,
                    scope="sync_diagnostics.read",
                    resource_type="sync_run",
                    purpose=normalized_purpose,
                )
            )
            await ComplianceService(self.session).record_audit_log(
                AuditLogCreate(
                    organization_id=grant.organization_id,
                    actor_type="support_user",
                    actor_id=support_user_id,
                    action="support.grant_used",
                    resource_type="sync_diagnostics",
                    resource_id=str(grant.id),
                    metadata={
                        "scope": "sync_diagnostics.read",
                        "purpose": normalized_purpose,
                    },
                )
            )
        return SupportDiagnosticResponse(
            grant_id=grant.id,
            organization_id=grant.organization_id,
            items=[
                SyncDiagnosticItem(
                    id=run.id,
                    connection_id=run.connection_id,
                    resource_type=run.resource_type,
                    status=run.status,
                    read_count=run.read_count,
                    created_count=run.created_count,
                    updated_count=run.updated_count,
                    failed_count=run.failed_count,
                    attempts=run.attempts,
                    error_summary=run.error_summary,
                    started_at=run.started_at,
                    finished_at=run.finished_at,
                )
                for run in runs
            ],
        )
