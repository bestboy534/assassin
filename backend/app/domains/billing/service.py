from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.applications.models import Application
from app.domains.organizations.models import OrganizationMember
from app.domains.organizations.service import OrganizationContext

from .models import (
    OrganizationEntitlement,
    OrganizationSubscription,
    Plan,
    PlanEntitlement,
    PlanPrice,
    UsageCounter,
    UsageEvent,
)

EntitlementValueType = Literal[
    "boolean",
    "integer",
    "metered",
    "duration",
    "support_tier",
]

STARTER_PLAN_KEY = "starter"
STARTER_ENTITLEMENTS: tuple[
    tuple[str, EntitlementValueType, bool | int | str, bool],
    ...,
] = (
    ("applications", "integer", 5, True),
    ("members", "integer", 5, True),
    ("api_access", "boolean", False, True),
    ("ai_pages", "metered", 100, False),
    ("storage_bytes", "metered", 1_073_741_824, True),
    ("retention_days", "duration", 30, True),
    ("support_tier", "support_tier", "standard", False),
)
VALID_VALUE_TYPES = {item[1] for item in STARTER_ENTITLEMENTS}


@dataclass(frozen=True)
class ResolvedEntitlement:
    key: str
    value_type: str
    value: bool | int | str
    hard_limit: bool
    plan: str
    overridden: bool


@dataclass(frozen=True)
class UsageResult:
    metric: str
    current_value: int
    period_start: datetime
    period_end: datetime
    duplicate: bool


class EntitlementDenied(Exception):
    def __init__(self, entitlement: str, *, plan: str) -> None:
        super().__init__(f"Entitlement is not enabled: {entitlement}")
        self.entitlement = entitlement
        self.plan = plan


class EntitlementExceeded(EntitlementDenied):
    def __init__(
        self,
        entitlement: str,
        *,
        current: int,
        limit: int,
        increment: int,
        plan: str,
    ) -> None:
        super().__init__(entitlement, plan=plan)
        self.current = current
        self.limit = limit
        self.increment = increment


class EntitlementConfigurationError(Exception):
    pass


class EntitlementService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_default_subscription(
        self,
        organization_id: UUID,
    ) -> OrganizationSubscription:
        existing = await self.session.scalar(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == organization_id
            )
        )
        if existing is not None:
            return existing

        async with transaction(self.session):
            plan = await self._ensure_starter_plan()
            subscription = OrganizationSubscription(
                organization_id=organization_id,
                plan_id=plan.id,
                status="active",
                provider="internal",
                provider_version=0,
                read_only=False,
                cancel_at_period_end=False,
            )
            self.session.add(subscription)
            await self.session.flush()
        return subscription

    async def resolve(
        self,
        organization_id: UUID,
        key: str,
    ) -> ResolvedEntitlement:
        subscription = await self.ensure_default_subscription(organization_id)
        plan = await self.session.get(Plan, subscription.plan_id)
        if plan is None:
            raise EntitlementConfigurationError("Subscription plan is missing")

        now = datetime.now(UTC)
        override = await self.session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization_id,
                OrganizationEntitlement.key == key,
                (OrganizationEntitlement.expires_at.is_(None))
                | (OrganizationEntitlement.expires_at > now),
            )
        )
        if override is not None:
            return ResolvedEntitlement(
                key=key,
                value_type=override.value_type,
                value=self._stored_value(override.value_json, key),
                hard_limit=True,
                plan=plan.key,
                overridden=True,
            )

        entitlement = await self.session.scalar(
            select(PlanEntitlement).where(
                PlanEntitlement.plan_id == plan.id,
                PlanEntitlement.key == key,
            )
        )
        if entitlement is None:
            raise EntitlementDenied(key, plan=plan.key)
        return ResolvedEntitlement(
            key=key,
            value_type=entitlement.value_type,
            value=self._stored_value(entitlement.value_json, key),
            hard_limit=entitlement.hard_limit,
            plan=plan.key,
            overridden=False,
        )

    async def require_feature(
        self,
        context: OrganizationContext,
        feature: str,
    ) -> None:
        entitlement = await self.resolve(context.organization_id, feature)
        if entitlement.value_type != "boolean" or entitlement.value is not True:
            raise EntitlementDenied(feature, plan=entitlement.plan)

    async def require_capacity(
        self,
        context: OrganizationContext,
        metric: str,
        increment: int = 1,
    ) -> None:
        if increment < 1:
            raise ValueError("Capacity increment must be positive")
        entitlement = await self.resolve(context.organization_id, metric)
        if entitlement.value_type not in {"integer", "metered"} or not isinstance(
            entitlement.value,
            int,
        ):
            raise EntitlementConfigurationError(
                f"Entitlement {metric} is not a numeric capacity"
            )
        current = await self._current_capacity(context.organization_id, metric)
        if entitlement.hard_limit and current + increment > entitlement.value:
            raise EntitlementExceeded(
                metric,
                current=current,
                limit=entitlement.value,
                increment=increment,
                plan=entitlement.plan,
            )

    async def record_usage(
        self,
        context: OrganizationContext,
        metric: str,
        amount: int,
        source_key: str,
        *,
        metadata: dict[str, object] | None = None,
        occurred_at: datetime | None = None,
    ) -> UsageResult:
        if amount < 1:
            raise ValueError("Usage amount must be positive")
        normalized_source = source_key.strip()
        if not normalized_source:
            raise ValueError("Usage source key is required")

        event_time = occurred_at or datetime.now(UTC)
        period_start, period_end = self._calendar_month(event_time)
        duplicate = await self.session.scalar(
            select(UsageEvent.id).where(
                UsageEvent.organization_id == context.organization_id,
                UsageEvent.metric == metric,
                UsageEvent.source_key == normalized_source,
            )
        )
        if duplicate is not None:
            counter = await self._usage_counter(
                context.organization_id,
                metric,
                period_start,
            )
            return UsageResult(
                metric=metric,
                current_value=counter.current_value if counter is not None else 0,
                period_start=period_start,
                period_end=period_end,
                duplicate=True,
            )

        async with transaction(self.session):
            counter = await self._usage_counter(
                context.organization_id,
                metric,
                period_start,
            )
            if counter is None:
                counter = UsageCounter(
                    organization_id=context.organization_id,
                    metric=metric,
                    period_start=period_start,
                    period_end=period_end,
                    current_value=0,
                    status="ok",
                )
                self.session.add(counter)
                await self.session.flush()
            self.session.add(
                UsageEvent(
                    organization_id=context.organization_id,
                    metric=metric,
                    amount=amount,
                    source_key=normalized_source,
                    metadata_json=metadata or {},
                    occurred_at=event_time,
                )
            )
            counter.current_value += amount
            await self.session.flush()

        return UsageResult(
            metric=metric,
            current_value=counter.current_value,
            period_start=period_start,
            period_end=period_end,
            duplicate=False,
        )

    async def set_organization_entitlement(
        self,
        organization_id: UUID,
        *,
        key: str,
        value_type: EntitlementValueType,
        value: bool | int | str,
        reason: str,
        expires_at: datetime | None = None,
    ) -> OrganizationEntitlement:
        self._validate_value(value_type, value)
        await self.ensure_default_subscription(organization_id)
        async with transaction(self.session):
            entitlement = await self.session.scalar(
                select(OrganizationEntitlement).where(
                    OrganizationEntitlement.organization_id == organization_id,
                    OrganizationEntitlement.key == key,
                )
            )
            if entitlement is None:
                entitlement = OrganizationEntitlement(
                    organization_id=organization_id,
                    key=key,
                    value_type=value_type,
                    value_json={"value": value},
                    reason=reason.strip(),
                    expires_at=expires_at,
                )
                self.session.add(entitlement)
            else:
                entitlement.value_type = value_type
                entitlement.value_json = {"value": value}
                entitlement.reason = reason.strip()
                entitlement.expires_at = expires_at
            await self.session.flush()
        return entitlement

    async def _ensure_starter_plan(self) -> Plan:
        plan = await self.session.scalar(select(Plan).where(Plan.key == STARTER_PLAN_KEY))
        if plan is None:
            plan = Plan(
                key=STARTER_PLAN_KEY,
                name="Starter",
                description="Default plan for existing and unconfigured organizations.",
                status="active",
                is_default=True,
            )
            self.session.add(plan)
            await self.session.flush()
            self.session.add(
                PlanPrice(
                    plan_id=plan.id,
                    currency="USD",
                    billing_interval="month",
                    amount_minor=0,
                    status="active",
                )
            )
            for key, value_type, value, hard_limit in STARTER_ENTITLEMENTS:
                self.session.add(
                    PlanEntitlement(
                        plan_id=plan.id,
                        key=key,
                        value_type=value_type,
                        value_json={"value": value},
                        hard_limit=hard_limit,
                    )
                )
            await self.session.flush()
        return plan

    async def _current_capacity(self, organization_id: UUID, metric: str) -> int:
        if metric == "applications":
            return int(
                await self.session.scalar(
                    select(func.count(Application.id)).where(
                        Application.organization_id == organization_id,
                        Application.status != "archived",
                    )
                )
                or 0
            )
        if metric == "members":
            return int(
                await self.session.scalar(
                    select(func.count(OrganizationMember.id)).where(
                        OrganizationMember.organization_id == organization_id,
                        OrganizationMember.status == "active",
                    )
                )
                or 0
            )
        now = datetime.now(UTC)
        period_start, _ = self._calendar_month(now)
        counter = await self._usage_counter(organization_id, metric, period_start)
        return counter.current_value if counter is not None else 0

    async def _usage_counter(
        self,
        organization_id: UUID,
        metric: str,
        period_start: datetime,
    ) -> UsageCounter | None:
        result = await self.session.execute(
            select(UsageCounter).where(
                UsageCounter.organization_id == organization_id,
                UsageCounter.metric == metric,
                UsageCounter.period_start == period_start,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _calendar_month(value: datetime) -> tuple[datetime, datetime]:
        normalized = value.astimezone(UTC)
        start = normalized.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    @staticmethod
    def _stored_value(value_json: dict[str, object], key: str) -> bool | int | str:
        value = value_json.get("value")
        if isinstance(value, bool | int | str):
            return value
        raise EntitlementConfigurationError(f"Entitlement {key} has an invalid value")

    @staticmethod
    def _validate_value(
        value_type: EntitlementValueType,
        value: bool | int | str,
    ) -> None:
        if value_type not in VALID_VALUE_TYPES:
            raise EntitlementConfigurationError(f"Unsupported entitlement type: {value_type}")
        if value_type == "boolean" and not isinstance(value, bool):
            raise EntitlementConfigurationError("Boolean entitlement requires bool value")
        if value_type in {"integer", "metered", "duration"} and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise EntitlementConfigurationError(
                f"{value_type} entitlement requires a non-negative integer"
            )
        if value_type == "support_tier" and (
            not isinstance(value, str) or not value.strip()
        ):
            raise EntitlementConfigurationError(
                "Support tier entitlement requires a non-empty string"
            )
