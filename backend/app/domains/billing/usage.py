from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .service import (
    EntitlementService,
    OrganizationScope,
    UsageResult,
)

USAGE_METRICS = (
    "members",
    "applications",
    "storage_bytes",
    "ai_pages",
    "integration_connections",
    "export_rows",
    "api_calls",
)


@dataclass(frozen=True)
class OrganizationUsageScope:
    organization_id: UUID


@dataclass(frozen=True)
class UsageMetricSnapshot:
    metric: str
    current_value: int
    limit: int
    hard_limit: bool
    status: str


class UsageService:
    def __init__(self, session: AsyncSession) -> None:
        self.entitlements = EntitlementService(session)

    async def record(
        self,
        context: OrganizationScope,
        metric: str,
        amount: int,
        *,
        source_key: str,
        metadata: dict[str, object] | None = None,
        occurred_at: datetime | None = None,
    ) -> UsageResult:
        self._require_metric(metric)
        return await self.entitlements.record_usage(
            context,
            metric,
            amount,
            source_key,
            metadata=metadata,
            occurred_at=occurred_at,
        )

    async def snapshot(
        self,
        context: OrganizationScope,
        *,
        now: datetime | None = None,
    ) -> list[UsageMetricSnapshot]:
        current_time = now or datetime.now(UTC)
        items: list[UsageMetricSnapshot] = []
        for metric in USAGE_METRICS:
            entitlement = await self.entitlements.resolve(
                context.organization_id,
                metric,
            )
            if (
                entitlement.value_type not in {"integer", "metered"}
                or isinstance(entitlement.value, bool)
                or not isinstance(entitlement.value, int)
            ):
                continue
            current = await self.entitlements.current_usage(
                context.organization_id,
                metric,
                now=current_time,
            )
            items.append(
                UsageMetricSnapshot(
                    metric=metric,
                    current_value=current,
                    limit=entitlement.value,
                    hard_limit=entitlement.hard_limit,
                    status=EntitlementService.usage_status(
                        current,
                        entitlement.value,
                    ),
                )
            )
        return items

    @staticmethod
    def _require_metric(metric: str) -> None:
        if metric not in USAGE_METRICS:
            raise ValueError(f"Unsupported usage metric: {metric}")
