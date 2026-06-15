from datetime import UTC, datetime
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.outbox.repository import OutboxRepository

from .models import (
    StatusComponent,
    StatusIncident,
    StatusIncidentUpdate,
    StatusSubscriber,
)
from .schemas import (
    PublicIncidentList,
    PublicIncidentUpdate,
    PublicStatusComponent,
    PublicStatusIncident,
    PublicStatusOverview,
    StatusSubscriptionResponse,
)

INCIDENT_STATUSES = ("investigating", "identified", "monitoring", "resolved")
COMPONENT_STATUSES = (
    "operational",
    "degraded",
    "partial_outage",
    "major_outage",
    "maintenance",
)
IMPACT_TO_COMPONENT_STATUS = {
    "degraded": "degraded",
    "partial_outage": "partial_outage",
    "major_outage": "major_outage",
    "maintenance": "maintenance",
}
STATUS_SEVERITY = {
    "operational": 0,
    "maintenance": 1,
    "degraded": 2,
    "partial_outage": 3,
    "major_outage": 4,
}


class StatusIncidentNotFound(Exception):
    pass


class InvalidIncidentTransition(Exception):
    pass


class StatusPageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.outbox = OutboxRepository(session)

    async def publish_incident(
        self,
        incident: StatusIncident,
        *,
        public_message: str,
        internal_note: str = "",
        now: datetime | None = None,
    ) -> StatusIncident:
        current_time = self._as_utc(now or datetime.now(UTC))
        if incident.impact not in IMPACT_TO_COMPONENT_STATUS:
            raise InvalidIncidentTransition("Unsupported incident impact")
        incident.status = "investigating"
        incident.started_at = current_time
        incident.updated_at = current_time
        async with transaction(self.session):
            self.session.add(incident)
            await self.session.flush()
            component = await self.session.get(
                StatusComponent,
                incident.status_component_id,
            )
            if component is None:
                raise StatusIncidentNotFound
            component.status = IMPACT_TO_COMPONENT_STATUS[incident.impact]
            component.updated_at = current_time
            self.session.add(
                StatusIncidentUpdate(
                    status_incident_id=incident.id,
                    status="investigating",
                    public_message=public_message.strip(),
                    internal_note=internal_note.strip(),
                    created_at=current_time,
                )
            )
            await self._queue_incident_notification(
                incident,
                status="investigating",
                public_message=public_message,
                occurred_at=current_time,
            )
        return incident

    async def add_incident_update(
        self,
        incident_id: UUID,
        *,
        status: str,
        public_message: str,
        internal_note: str = "",
        now: datetime | None = None,
    ) -> StatusIncident:
        incident = await self.session.get(StatusIncident, incident_id)
        if incident is None:
            raise StatusIncidentNotFound
        self._validate_transition(incident.status, status)
        current_time = self._as_utc(now or datetime.now(UTC))
        async with transaction(self.session):
            incident.status = status
            incident.updated_at = current_time
            self.session.add(
                StatusIncidentUpdate(
                    status_incident_id=incident.id,
                    status=status,
                    public_message=public_message.strip(),
                    internal_note=internal_note.strip(),
                    created_at=current_time,
                )
            )
            if status == "resolved":
                incident.resolved_at = current_time
                await self.session.flush()
                active_other = await self.session.scalar(
                    select(StatusIncident.id)
                    .where(
                        StatusIncident.status_component_id
                        == incident.status_component_id,
                        StatusIncident.id != incident.id,
                        StatusIncident.status != "resolved",
                    )
                    .limit(1)
                )
                if active_other is None:
                    component = await self.session.get(
                        StatusComponent,
                        incident.status_component_id,
                    )
                    if component is not None:
                        component.status = "operational"
                        component.updated_at = current_time
            await self._queue_incident_notification(
                incident,
                status=status,
                public_message=public_message,
                occurred_at=current_time,
            )
        return incident

    async def overview(self) -> PublicStatusOverview:
        components = list(
            (
                await self.session.scalars(
                    select(StatusComponent).order_by(
                        StatusComponent.display_order,
                        StatusComponent.name,
                    )
                )
            ).all()
        )
        incidents = await self._incident_responses(active_only=True)
        overall = max(
            (component.status for component in components),
            key=lambda item: STATUS_SEVERITY.get(item, 0),
            default="operational",
        )
        return PublicStatusOverview(
            overall_status=overall,
            generated_at=datetime.now(UTC),
            components=[
                PublicStatusComponent(
                    id=component.id,
                    slug=component.slug,
                    name=component.name,
                    description=component.description,
                    status=component.status,
                )
                for component in components
            ],
            incidents=incidents,
        )

    async def incidents(self) -> PublicIncidentList:
        return PublicIncidentList(items=await self._incident_responses(active_only=False))

    async def subscribe(self, email: str) -> StatusSubscriptionResponse:
        normalized = email.strip().lower()
        existing = await self.session.scalar(
            select(StatusSubscriber).where(
                StatusSubscriber.email_normalized == normalized
            )
        )
        if existing is not None:
            return StatusSubscriptionResponse(status=existing.status)
        raw_token = token_urlsafe(32)
        subscriber = StatusSubscriber(
            email_normalized=normalized,
            confirmation_token_hash=sha256(raw_token.encode()).hexdigest(),
        )
        async with transaction(self.session):
            self.session.add(subscriber)
            await self.session.flush()
            await self.outbox.add(
                "status.subscription_confirmation",
                subscriber.id,
                {
                    "subscriber_id": str(subscriber.id),
                    "email": normalized,
                    "confirmation_token": raw_token,
                },
            )
        return StatusSubscriptionResponse(status=subscriber.status)

    async def _incident_responses(
        self,
        *,
        active_only: bool,
    ) -> list[PublicStatusIncident]:
        statement = (
            select(StatusIncident, StatusComponent)
            .join(
                StatusComponent,
                StatusComponent.id == StatusIncident.status_component_id,
            )
            .order_by(StatusIncident.started_at.desc())
        )
        if active_only:
            statement = statement.where(StatusIncident.status != "resolved")
        rows = (await self.session.execute(statement)).all()
        responses: list[PublicStatusIncident] = []
        for incident, component in rows:
            updates = list(
                (
                    await self.session.scalars(
                        select(StatusIncidentUpdate)
                        .where(
                            StatusIncidentUpdate.status_incident_id == incident.id
                        )
                        .order_by(StatusIncidentUpdate.created_at.desc())
                    )
                ).all()
            )
            responses.append(
                PublicStatusIncident(
                    id=incident.id,
                    component_id=component.id,
                    component_name=component.name,
                    title=incident.title,
                    summary=incident.public_summary,
                    impact=incident.impact,
                    status=incident.status,
                    started_at=incident.started_at,
                    resolved_at=incident.resolved_at,
                    postmortem_summary=incident.postmortem_summary,
                    updates=[
                        PublicIncidentUpdate(
                            id=update.id,
                            status=update.status,
                            message=update.public_message,
                            created_at=update.created_at,
                        )
                        for update in updates
                    ],
                )
            )
        return responses

    async def _queue_incident_notification(
        self,
        incident: StatusIncident,
        *,
        status: str,
        public_message: str,
        occurred_at: datetime,
    ) -> None:
        await self.outbox.add(
            "status.incident_updated",
            f"{incident.id}:{status}:{occurred_at.isoformat()}",
            {
                "incident_id": str(incident.id),
                "component_id": str(incident.status_component_id),
                "title": incident.title,
                "status": status,
                "message": public_message.strip(),
                "occurred_at": occurred_at.isoformat(),
            },
        )

    @staticmethod
    def _validate_transition(current: str, target: str) -> None:
        if target not in INCIDENT_STATUSES:
            raise InvalidIncidentTransition("Unsupported incident status")
        if current == "resolved":
            raise InvalidIncidentTransition("Resolved incident cannot be reopened")
        if INCIDENT_STATUSES.index(target) < INCIDENT_STATUSES.index(current):
            raise InvalidIncidentTransition("Incident status cannot move backwards")

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
