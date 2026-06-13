from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.database import Database
from app.domains.applications.models import Application
from app.domains.billing.models import OrganizationSubscription, Plan
from app.domains.billing.plan_changes import PlanChangeService
from app.domains.billing.service import EntitlementService
from app.domains.identity.models import User
from app.domains.identity.service import IdentityService
from app.domains.organizations.models import Organization, OrganizationMember


async def _organization(session, email: str) -> Organization:
    user, _ = await IdentityService(session).register(
        email=email,
        password="Long passphrase 2026!",
        display_name="Plan Owner",
        organization_name=f"{email} Org",
        user_agent="pytest",
    )
    organization = await session.scalar(
        select(Organization).where(Organization.created_by_user_id == user.id)
    )
    assert organization is not None
    return organization


async def test_downgrade_preview_lists_over_limit_resources_without_deleting(
    database: Database,
) -> None:
    now = datetime(2026, 6, 13, 9, 0, tzinfo=UTC)
    period_end = now + timedelta(days=18)
    async with database.session_factory() as session:
        organization = await _organization(session, "downgrade@example.com")
        entitlement_service = EntitlementService(session)
        pro = await entitlement_service.ensure_plan("pro")
        subscription = await session.scalar(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == organization.id
            )
        )
        assert subscription is not None
        subscription.plan_id = pro.id
        subscription.status = "active"
        subscription.current_period_start = now - timedelta(days=12)
        subscription.current_period_end = period_end

        owner = await session.scalar(
            select(User).where(User.id == organization.created_by_user_id)
        )
        assert owner is not None
        for index in range(12):
            member = User(
                email_normalized=f"downgrade-member-{index}@example.com",
                password_hash="test",
                display_name=f"Member {index}",
                status="active",
                email_verified_at=User.verified_now(),
            )
            session.add(member)
            await session.flush()
            session.add(
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=member.id,
                    role="member",
                    status="active",
                )
            )
        for index in range(48):
            session.add(
                Application(
                    organization_id=organization.id,
                    name=f"Pro App {index}",
                    name_normalized=f"pro app {index}",
                    category="productivity",
                    status="active",
                    risk_level="unknown",
                    approved=False,
                    created_by_user_id=owner.id,
                )
            )
        await session.flush()

        service = PlanChangeService(session)
        preview = await service.preview_change(
            organization.id,
            target_plan="starter",
            now=now,
        )

        assert preview.direction == "downgrade"
        assert preview.effective_at == period_end
        assert preview.proration_minor == 0
        assert preview.over_limit == {"members": 8, "applications": 43}
        assert "api_access" in preview.lost_features

        scheduled = await service.change_plan(
            organization.id,
            target_plan="starter",
            now=now,
        )
        assert scheduled.plan_id == pro.id
        assert scheduled.pending_plan_id is not None
        assert scheduled.pending_change_at == period_end

        assert await service.apply_scheduled_changes(now=period_end) == 1
        changed = await service.get(organization.id)
        starter = await session.scalar(select(Plan).where(Plan.key == "starter"))
        assert starter is not None
        assert changed.plan_id == starter.id
        assert changed.pending_plan_id is None
        assert (
            await session.scalar(
                select(func.count(Application.id)).where(
                    Application.organization_id == organization.id
                )
            )
            == 48
        )
        assert (
            await session.scalar(
                select(func.count(OrganizationMember.id)).where(
                    OrganizationMember.organization_id == organization.id
                )
            )
            == 13
        )


async def test_upgrade_is_immediate_and_cancellation_can_be_undone(
    database: Database,
) -> None:
    now = datetime(2026, 6, 13, 9, 0, tzinfo=UTC)
    async with database.session_factory() as session:
        organization = await _organization(session, "upgrade@example.com")
        service = PlanChangeService(session)
        subscription = await service.get(organization.id)
        subscription.status = "active"
        subscription.current_period_start = now - timedelta(days=10)
        subscription.current_period_end = now + timedelta(days=20)
        await session.flush()

        preview = await service.preview_change(
            organization.id,
            target_plan="pro",
            now=now,
        )
        upgraded = await service.change_plan(
            organization.id,
            target_plan="pro",
            now=now,
        )
        pro = await session.scalar(select(Plan).where(Plan.key == "pro"))

        assert pro is not None
        assert preview.direction == "upgrade"
        assert preview.effective_at == now
        assert preview.current_amount_minor == 0
        assert preview.target_amount_minor == 4900
        assert preview.proration_minor > 0
        assert upgraded.plan_id == pro.id
        assert upgraded.pending_plan_id is None

        cancelled = await service.cancel_at_period_end(organization.id)
        assert cancelled.status == "cancel_at_period_end"
        assert cancelled.cancel_at_period_end is True
        restored = await service.undo_cancellation(organization.id)
        assert restored.status == "active"
        assert restored.cancel_at_period_end is False
