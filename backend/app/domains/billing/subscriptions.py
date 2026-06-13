from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.outbox.models import OutboxEvent
from app.domains.outbox.repository import OutboxRepository

from .models import OrganizationSubscription
from .service import EntitlementService

DEFAULT_TRIAL_DAYS = 14
MAX_TRIAL_EXTENSION_DAYS = 30
TRIAL_REMINDER_DAYS = (3, 1)
SUBSCRIPTION_STATUSES = {
    "trialing",
    "trial_expired",
    "active",
    "past_due",
    "grace_period",
    "suspended",
    "cancel_at_period_end",
    "cancelled",
    "enterprise_contract",
}
READ_ONLY_STATUSES = {"trial_expired", "suspended", "cancelled"}


class SubscriptionNotFound(Exception):
    pass


class InvalidSubscriptionState(Exception):
    pass


class SubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.outbox = OutboxRepository(session)

    async def get(self, organization_id: UUID) -> OrganizationSubscription:
        result = await self.session.execute(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == organization_id
            )
        )
        subscription = result.scalar_one_or_none()
        if subscription is None:
            raise SubscriptionNotFound
        return subscription

    async def start_trial(
        self,
        organization_id: UUID,
        *,
        days: int = DEFAULT_TRIAL_DAYS,
        now: datetime | None = None,
    ) -> OrganizationSubscription:
        if days < 1:
            raise ValueError("Trial duration must be positive")
        started_at = self._as_utc(now or datetime.now(UTC))
        subscription = await EntitlementService(
            self.session
        ).ensure_default_subscription(organization_id)
        async with transaction(self.session):
            subscription.status = "trialing"
            subscription.read_only = False
            subscription.started_at = started_at
            subscription.trial_ends_at = started_at + timedelta(days=days)
            subscription.cancel_at_period_end = False
            subscription.cancelled_at = None
            await self.outbox.add(
                "billing.trial_started",
                subscription.id,
                {
                    "organization_id": str(organization_id),
                    "subscription_id": str(subscription.id),
                    "trial_ends_at": subscription.trial_ends_at.isoformat(),
                },
                organization_id=organization_id,
            )
        return subscription

    async def extend_trial(
        self,
        organization_id: UUID,
        *,
        days: int,
        reason: str,
        now: datetime | None = None,
    ) -> OrganizationSubscription:
        if days < 1 or days > MAX_TRIAL_EXTENSION_DAYS:
            raise ValueError(
                f"Trial extension must be between 1 and {MAX_TRIAL_EXTENSION_DAYS} days"
            )
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValueError("Trial extension reason is required")

        subscription = await self.get(organization_id)
        if subscription.status not in {"trialing", "trial_expired"}:
            raise InvalidSubscriptionState(
                f"Cannot extend a subscription in {subscription.status} state"
            )
        current_time = self._as_utc(now or datetime.now(UTC))
        previous_end = self._as_utc(subscription.trial_ends_at or current_time)
        extension_base = max(previous_end, current_time)

        async with transaction(self.session):
            subscription.status = "trialing"
            subscription.read_only = False
            subscription.trial_ends_at = extension_base + timedelta(days=days)
            await self.outbox.add(
                "billing.trial_extended",
                subscription.id,
                {
                    "organization_id": str(organization_id),
                    "subscription_id": str(subscription.id),
                    "previous_trial_ends_at": previous_end.isoformat(),
                    "trial_ends_at": subscription.trial_ends_at.isoformat(),
                    "extension_days": days,
                    "reason": normalized_reason,
                },
                organization_id=organization_id,
            )
        return subscription

    async def expire_trials(self, *, now: datetime | None = None) -> int:
        current_time = self._as_utc(now or datetime.now(UTC))
        subscriptions = list(
            (
                await self.session.scalars(
                    select(OrganizationSubscription).where(
                        OrganizationSubscription.status == "trialing",
                        OrganizationSubscription.trial_ends_at.is_not(None),
                        OrganizationSubscription.trial_ends_at <= current_time,
                    )
                )
            ).all()
        )
        if not subscriptions:
            return 0

        async with transaction(self.session):
            for subscription in subscriptions:
                subscription.status = "trial_expired"
                subscription.read_only = True
                await self.outbox.add(
                    "billing.trial_expired",
                    subscription.id,
                    {
                        "organization_id": str(subscription.organization_id),
                        "subscription_id": str(subscription.id),
                        "trial_ends_at": self._as_utc(
                            subscription.trial_ends_at or current_time
                        ).isoformat(),
                    },
                    organization_id=subscription.organization_id,
                )
        return len(subscriptions)

    async def queue_trial_reminders(self, *, now: datetime | None = None) -> int:
        current_time = self._as_utc(now or datetime.now(UTC))
        reminder_limit = current_time + timedelta(days=max(TRIAL_REMINDER_DAYS))
        subscriptions = list(
            (
                await self.session.scalars(
                    select(OrganizationSubscription).where(
                        OrganizationSubscription.status == "trialing",
                        OrganizationSubscription.trial_ends_at.is_not(None),
                        OrganizationSubscription.trial_ends_at > current_time,
                        OrganizationSubscription.trial_ends_at <= reminder_limit,
                    )
                )
            ).all()
        )
        queued = 0
        async with transaction(self.session):
            for subscription in subscriptions:
                trial_end = self._as_utc(subscription.trial_ends_at or current_time)
                remaining = trial_end - current_time
                reminder_days = 1 if remaining <= timedelta(days=1) else 3
                aggregate_id = f"{subscription.id}:trial-ending:{reminder_days}d"
                existing = await self.session.scalar(
                    select(OutboxEvent.id).where(
                        OutboxEvent.event_type == "billing.trial_ending",
                        OutboxEvent.aggregate_id == aggregate_id,
                    )
                )
                if existing is not None:
                    continue
                await self.outbox.add(
                    "billing.trial_ending",
                    aggregate_id,
                    {
                        "organization_id": str(subscription.organization_id),
                        "subscription_id": str(subscription.id),
                        "trial_ends_at": trial_end.isoformat(),
                        "days_remaining": reminder_days,
                    },
                    organization_id=subscription.organization_id,
                )
                queued += 1
        return queued

    async def transition(
        self,
        organization_id: UUID,
        status: str,
    ) -> OrganizationSubscription:
        if status not in SUBSCRIPTION_STATUSES:
            raise InvalidSubscriptionState(f"Unsupported subscription state: {status}")
        subscription = await self.get(organization_id)
        async with transaction(self.session):
            subscription.status = status
            subscription.read_only = status in READ_ONLY_STATUSES
            subscription.cancel_at_period_end = status == "cancel_at_period_end"
            if status == "cancelled":
                subscription.cancelled_at = datetime.now(UTC)
            elif status != "cancel_at_period_end":
                subscription.cancelled_at = None
        return subscription

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
