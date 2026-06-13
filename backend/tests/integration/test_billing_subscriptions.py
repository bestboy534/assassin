from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.database import Database
from app.domains.applications.models import Application
from app.domains.billing.models import OrganizationSubscription
from app.domains.billing.subscriptions import (
    DEFAULT_TRIAL_DAYS,
    SUBSCRIPTION_STATUSES,
    SubscriptionService,
)
from app.domains.identity.models import User
from app.domains.identity.service import IdentityService
from app.domains.organizations.models import Organization
from app.domains.outbox.models import OutboxEvent


async def test_expired_trial_becomes_read_only_without_deleting_data(
    database: Database,
) -> None:
    started_at = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
    async with database.session_factory() as session:
        user = User(
            email_normalized="trial-owner@example.com",
            password_hash="test",
            display_name="Trial Owner",
            status="active",
            email_verified_at=User.verified_now(),
        )
        session.add(user)
        await session.flush()
        organization = Organization(
            name="Trial Org",
            slug="trial-org",
            status="active",
            created_by_user_id=user.id,
        )
        session.add(organization)
        await session.flush()
        session.add(
            Application(
                organization_id=organization.id,
                name="Retained App",
                name_normalized="retained app",
                category="productivity",
                status="active",
                risk_level="unknown",
                approved=False,
                created_by_user_id=user.id,
            )
        )
        await session.flush()

        service = SubscriptionService(session)
        trial = await service.start_trial(organization.id, now=started_at)

        assert trial.status == "trialing"
        assert trial.read_only is False
        assert trial.trial_ends_at == started_at + timedelta(days=DEFAULT_TRIAL_DAYS)

        expired_count = await service.expire_trials(
            now=trial.trial_ends_at + timedelta(seconds=1)
        )
        expired = await service.get(organization.id)

        assert expired_count == 1
        assert expired.status == "trial_expired"
        assert expired.read_only is True
        assert await session.get(Organization, organization.id) is not None
        assert (
            await session.scalar(
                select(func.count(Application.id)).where(
                    Application.organization_id == organization.id
                )
            )
            == 1
        )


async def test_trial_reminders_are_idempotent_and_trial_can_be_extended(
    database: Database,
) -> None:
    started_at = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
    async with database.session_factory() as session:
        user = User(
            email_normalized="trial-reminder@example.com",
            password_hash="test",
            display_name="Trial Reminder",
            status="active",
            email_verified_at=User.verified_now(),
        )
        session.add(user)
        await session.flush()
        organization = Organization(
            name="Trial Reminder Org",
            slug="trial-reminder-org",
            status="active",
            created_by_user_id=user.id,
        )
        session.add(organization)
        await session.flush()

        service = SubscriptionService(session)
        trial = await service.start_trial(organization.id, now=started_at)
        assert trial.trial_ends_at is not None
        reminder_time = trial.trial_ends_at - timedelta(days=3)

        assert await service.queue_trial_reminders(now=reminder_time) == 1
        assert await service.queue_trial_reminders(now=reminder_time) == 0
        assert (
            await session.scalar(
                select(func.count(OutboxEvent.id)).where(
                    OutboxEvent.organization_id == organization.id,
                    OutboxEvent.event_type == "billing.trial_ending",
                )
            )
            == 1
        )

        original_end = trial.trial_ends_at
        extended = await service.extend_trial(
            organization.id,
            days=7,
            reason="Pilot evaluation needs another week",
            now=started_at + timedelta(days=13),
        )

        assert extended.status == "trialing"
        assert extended.read_only is False
        assert extended.trial_ends_at == original_end + timedelta(days=7)


async def test_registration_starts_default_trial_and_statuses_are_declared(
    database: Database,
) -> None:
    expected_statuses = {
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
    assert SUBSCRIPTION_STATUSES == expected_statuses

    async with database.session_factory() as session:
        user, _ = await IdentityService(session).register(
            email="new-trial@example.com",
            password="Long passphrase 2026!",
            display_name="New Trial",
            organization_name="New Trial Org",
            user_agent="pytest",
        )
        organization = await session.scalar(
            select(Organization).where(Organization.created_by_user_id == user.id)
        )
        assert organization is not None
        subscription = await session.scalar(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == organization.id
            )
        )

        assert subscription is not None
        assert subscription.status == "trialing"
        assert subscription.read_only is False
        assert subscription.trial_ends_at is not None

        service = SubscriptionService(session)
        assert (await service.transition(organization.id, "past_due")).read_only is False
        assert (await service.transition(organization.id, "grace_period")).read_only is False
        assert (await service.transition(organization.id, "suspended")).read_only is True
        assert (
            await service.transition(organization.id, "enterprise_contract")
        ).read_only is False
        ending = await service.transition(organization.id, "cancel_at_period_end")
        assert ending.read_only is False
        assert ending.cancel_at_period_end is True
        cancelled = await service.transition(organization.id, "cancelled")
        assert cancelled.read_only is True
        assert cancelled.cancelled_at is not None
