from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, func, select

from app.core.database import Database
from app.domains.applications.models import Application
from app.domains.billing.models import PlanEntitlement, UsageCounter
from app.domains.billing.service import EntitlementExceeded, EntitlementService
from app.domains.billing.usage import USAGE_METRICS, UsageService
from app.domains.files.models import StoredFile
from app.domains.identity.models import User
from app.domains.identity.service import IdentityService
from app.domains.integrations.models import (
    IntegrationConnection,
    IntegrationDefinition,
)
from app.domains.organizations.models import Organization
from app.domains.organizations.service import OrganizationContext
from app.domains.outbox.models import OutboxEvent


async def _context(session, email: str) -> tuple[Organization, OrganizationContext]:
    user, _ = await IdentityService(session).register(
        email=email,
        password="Long passphrase 2026!",
        display_name="Usage Owner",
        organization_name=f"{email} Org",
        user_agent="pytest",
    )
    organization = await session.scalar(
        select(Organization).where(Organization.created_by_user_id == user.id)
    )
    assert organization is not None
    return organization, OrganizationContext(
        organization_id=organization.id,
        user_id=user.id,
        membership_id=user.id,
        role="owner",
    )


async def test_soft_limit_records_overage_and_threshold_notifications_once(
    database: Database,
) -> None:
    occurred_at = datetime(2026, 6, 13, 9, 0, tzinfo=UTC)
    async with database.session_factory() as session:
        organization, context = await _context(
            session,
            "usage-soft@example.com",
        )
        service = UsageService(session)

        below = await service.record(
            context,
            "ai_pages",
            79,
            source_key="job-79",
            occurred_at=occurred_at,
        )
        warning = await service.record(
            context,
            "ai_pages",
            1,
            source_key="job-80",
            occurred_at=occurred_at,
        )
        overage = await service.record(
            context,
            "ai_pages",
            21,
            source_key="job-101",
            occurred_at=occurred_at,
        )
        duplicate = await service.record(
            context,
            "ai_pages",
            21,
            source_key="job-101",
            occurred_at=occurred_at,
        )

        assert below.status == "ok"
        assert warning.status == "warning"
        assert warning.thresholds_queued == [80]
        assert overage.current_value == 101
        assert overage.status == "overage"
        assert overage.thresholds_queued == [100]
        assert duplicate.duplicate is True
        assert duplicate.current_value == 101
        assert (
            await session.scalar(
                select(func.count(OutboxEvent.id)).where(
                    OutboxEvent.organization_id == organization.id,
                    OutboxEvent.event_type == "billing.usage_threshold",
                )
            )
            == 2
        )


async def test_hard_limit_rejects_usage_before_counter_changes(
    database: Database,
) -> None:
    occurred_at = datetime(2026, 6, 13, 9, 0, tzinfo=UTC)
    async with database.session_factory() as session:
        organization, context = await _context(
            session,
            "usage-hard@example.com",
        )
        entitlements = EntitlementService(session)
        await entitlements.set_organization_entitlement(
            organization.id,
            key="api_calls",
            value_type="metered",
            value=10,
            reason="Hard limit test",
        )
        service = UsageService(session)

        warning = await service.record(
            context,
            "api_calls",
            8,
            source_key="request-8",
            occurred_at=occurred_at,
        )
        limit = await service.record(
            context,
            "api_calls",
            2,
            source_key="request-10",
            occurred_at=occurred_at,
        )
        with pytest.raises(EntitlementExceeded):
            await service.record(
                context,
                "api_calls",
                1,
                source_key="request-11",
                occurred_at=occurred_at,
            )

        assert warning.status == "warning"
        assert limit.status == "limit_reached"
        counter = await session.scalar(
            select(UsageCounter).where(
                UsageCounter.organization_id == organization.id,
                UsageCounter.metric == "api_calls",
            )
        )
        assert counter is not None
        assert counter.current_value == 10


async def test_usage_snapshot_contains_all_product_metrics(
    database: Database,
) -> None:
    occurred_at = datetime(2026, 6, 13, 9, 0, tzinfo=UTC)
    async with database.session_factory() as session:
        organization, context = await _context(
            session,
            "usage-snapshot@example.com",
        )
        owner = await session.get(User, context.user_id)
        assert owner is not None
        session.add(
            Application(
                organization_id=organization.id,
                name="Metered App",
                name_normalized="metered app",
                category="productivity",
                status="active",
                risk_level="unknown",
                approved=False,
                created_by_user_id=owner.id,
            )
        )
        session.add(
            StoredFile(
                organization_id=organization.id,
                filename="usage.csv",
                content_type="text/csv",
                size_bytes=321,
                status="available",
                quarantine_key=f"usage/{organization.id}/file",
                storage_key=f"files/{organization.id}/file",
            )
        )
        definition = IntegrationDefinition(
            key="usage-provider",
            name="Usage Provider",
            provider="usage",
            category="identity",
            auth_type="api_key",
            capabilities_json="[]",
            resource_types_json="[]",
            status="available",
        )
        session.add(definition)
        await session.flush()
        session.add(
            IntegrationConnection(
                organization_id=organization.id,
                definition_id=definition.id,
                created_by_user_id=owner.id,
                display_name="Usage connection",
                status="connected",
                auth_type="api_key",
                credential_label="usage",
                credential_last4="1234",
                sandbox_options_json="{}",
            )
        )
        await session.flush()
        service = UsageService(session)
        await service.record(
            context,
            "ai_pages",
            3,
            source_key="snapshot-ai",
            occurred_at=occurred_at,
        )
        await service.record(
            context,
            "export_rows",
            25,
            source_key="snapshot-export",
            occurred_at=occurred_at,
        )
        await service.record(
            context,
            "api_calls",
            7,
            source_key="snapshot-api",
            occurred_at=occurred_at,
        )

        snapshot = await service.snapshot(context, now=occurred_at)
        values = {item.metric: item.current_value for item in snapshot}

        assert set(values) == set(USAGE_METRICS)
        assert values["members"] == 1
        assert values["applications"] == 1
        assert values["storage_bytes"] == 321
        assert values["ai_pages"] == 3
        assert values["integration_connections"] == 1
        assert values["export_rows"] == 25
        assert values["api_calls"] == 7


async def test_existing_plan_catalog_is_reconciled_with_new_usage_metrics(
    database: Database,
) -> None:
    async with database.session_factory() as session:
        service = EntitlementService(session)
        starter = await service.ensure_plan("starter")
        await session.execute(
            delete(PlanEntitlement).where(
                PlanEntitlement.plan_id == starter.id,
                PlanEntitlement.key == "api_calls",
            )
        )
        await session.flush()

        await service.ensure_plan("starter")
        restored = await session.scalar(
            select(PlanEntitlement).where(
                PlanEntitlement.plan_id == starter.id,
                PlanEntitlement.key == "api_calls",
            )
        )

        assert restored is not None
        assert restored.value_json == {"value": 1000}
        assert restored.hard_limit is True
