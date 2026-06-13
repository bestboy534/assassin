from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.applications.models import Application
from app.domains.organizations.models import OrganizationMember

from .models import (
    OrganizationSubscription,
    Plan,
    PlanEntitlement,
    PlanPrice,
)
from .service import EntitlementService


class PlanChangeNotAllowed(Exception):
    pass


class SubscriptionNotFound(Exception):
    pass


@dataclass(frozen=True)
class PlanChangePreview:
    current_plan: str
    target_plan: str
    direction: str
    effective_at: datetime
    current_amount_minor: int
    target_amount_minor: int
    proration_minor: int
    lost_features: list[str]
    over_limit: dict[str, int]


class PlanChangeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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

    async def preview_change(
        self,
        organization_id: UUID,
        *,
        target_plan: str,
        now: datetime | None = None,
    ) -> PlanChangePreview:
        current_time = self._as_utc(now or datetime.now(UTC))
        subscription = await self.get(organization_id)
        current = await self._plan(subscription.plan_id)
        target = await EntitlementService(self.session).ensure_plan(target_plan)
        if current.id == target.id:
            raise PlanChangeNotAllowed("Organization already uses the target plan")

        current_amount = await self._monthly_amount(current.id)
        target_amount = await self._monthly_amount(target.id)
        direction = "upgrade" if target_amount > current_amount else "downgrade"
        effective_at = (
            current_time
            if direction == "upgrade"
            else self._as_utc(subscription.current_period_end or current_time)
        )
        proration = (
            self._proration(
                current_amount=current_amount,
                target_amount=target_amount,
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                now=current_time,
            )
            if direction == "upgrade"
            else 0
        )
        current_entitlements = await self._entitlements(current.id)
        target_entitlements = await self._entitlements(target.id)
        lost_features = sorted(
            key
            for key, value in current_entitlements.items()
            if value == ("boolean", True)
            and target_entitlements.get(key) != ("boolean", True)
        )
        over_limit = await self._over_limit(
            organization_id,
            target_entitlements,
        )
        return PlanChangePreview(
            current_plan=current.key,
            target_plan=target.key,
            direction=direction,
            effective_at=effective_at,
            current_amount_minor=current_amount,
            target_amount_minor=target_amount,
            proration_minor=proration,
            lost_features=lost_features,
            over_limit=over_limit,
        )

    async def change_plan(
        self,
        organization_id: UUID,
        *,
        target_plan: str,
        now: datetime | None = None,
    ) -> OrganizationSubscription:
        preview = await self.preview_change(
            organization_id,
            target_plan=target_plan,
            now=now,
        )
        subscription = await self.get(organization_id)
        target = await EntitlementService(self.session).ensure_plan(target_plan)
        async with transaction(self.session):
            if preview.direction == "upgrade":
                subscription.plan_id = target.id
                self._clear_pending(subscription)
                subscription.status = "active"
                subscription.read_only = False
            else:
                subscription.pending_plan_id = target.id
                subscription.pending_change_at = preview.effective_at
                subscription.pending_change_type = "downgrade"
        return subscription

    async def apply_scheduled_changes(
        self,
        *,
        now: datetime | None = None,
    ) -> int:
        current_time = self._as_utc(now or datetime.now(UTC))
        subscriptions = list(
            (
                await self.session.scalars(
                    select(OrganizationSubscription).where(
                        OrganizationSubscription.pending_plan_id.is_not(None),
                        OrganizationSubscription.pending_change_at.is_not(None),
                        OrganizationSubscription.pending_change_at <= current_time,
                    )
                )
            ).all()
        )
        async with transaction(self.session):
            for subscription in subscriptions:
                assert subscription.pending_plan_id is not None
                subscription.plan_id = subscription.pending_plan_id
                self._clear_pending(subscription)
        return len(subscriptions)

    async def cancel_at_period_end(
        self,
        organization_id: UUID,
    ) -> OrganizationSubscription:
        subscription = await self.get(organization_id)
        if subscription.status == "cancelled":
            raise PlanChangeNotAllowed("Cancelled subscription cannot be scheduled again")
        async with transaction(self.session):
            subscription.status = "cancel_at_period_end"
            subscription.cancel_at_period_end = True
        return subscription

    async def undo_cancellation(
        self,
        organization_id: UUID,
    ) -> OrganizationSubscription:
        subscription = await self.get(organization_id)
        if not subscription.cancel_at_period_end:
            raise PlanChangeNotAllowed("Subscription is not scheduled for cancellation")
        async with transaction(self.session):
            subscription.status = "active"
            subscription.cancel_at_period_end = False
            subscription.cancelled_at = None
        return subscription

    async def _plan(self, plan_id: UUID) -> Plan:
        plan = await self.session.get(Plan, plan_id)
        if plan is None:
            raise PlanChangeNotAllowed("Current subscription plan is missing")
        return plan

    async def _monthly_amount(self, plan_id: UUID) -> int:
        amount = await self.session.scalar(
            select(PlanPrice.amount_minor).where(
                PlanPrice.plan_id == plan_id,
                PlanPrice.currency == "USD",
                PlanPrice.billing_interval == "month",
                PlanPrice.status == "active",
            )
        )
        if amount is None:
            raise PlanChangeNotAllowed("Active monthly USD price is missing")
        return int(amount)

    async def _entitlements(
        self,
        plan_id: UUID,
    ) -> dict[str, tuple[str, object]]:
        rows = (
            await self.session.scalars(
                select(PlanEntitlement).where(PlanEntitlement.plan_id == plan_id)
            )
        ).all()
        return {
            row.key: (row.value_type, row.value_json.get("value"))
            for row in rows
        }

    async def _over_limit(
        self,
        organization_id: UUID,
        entitlements: dict[str, tuple[str, object]],
    ) -> dict[str, int]:
        counts = {
            "applications": int(
                await self.session.scalar(
                    select(func.count(Application.id)).where(
                        Application.organization_id == organization_id,
                        Application.status != "archived",
                    )
                )
                or 0
            ),
            "members": int(
                await self.session.scalar(
                    select(func.count(OrganizationMember.id)).where(
                        OrganizationMember.organization_id == organization_id,
                        OrganizationMember.status == "active",
                    )
                )
                or 0
            ),
        }
        over_limit: dict[str, int] = {}
        for key, current in counts.items():
            value_type, value = entitlements.get(key, ("integer", 0))
            if (
                value_type == "integer"
                and isinstance(value, int)
                and not isinstance(value, bool)
                and current > value
            ):
                over_limit[key] = current - value
        return over_limit

    @staticmethod
    def _proration(
        *,
        current_amount: int,
        target_amount: int,
        period_start: datetime | None,
        period_end: datetime | None,
        now: datetime,
    ) -> int:
        difference = max(target_amount - current_amount, 0)
        if period_start is None or period_end is None:
            return difference
        start = PlanChangeService._as_utc(period_start)
        end = PlanChangeService._as_utc(period_end)
        if end <= start or now >= end:
            return difference
        remaining = max((end - max(now, start)).total_seconds(), 0)
        total = (end - start).total_seconds()
        return round(difference * remaining / total)

    @staticmethod
    def _clear_pending(subscription: OrganizationSubscription) -> None:
        subscription.pending_plan_id = None
        subscription.pending_change_at = None
        subscription.pending_change_type = None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
