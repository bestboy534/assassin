from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.billing.models import OrganizationSubscription, Plan
from app.domains.billing.service import EntitlementService
from app.domains.identity.models import User
from app.domains.identity.security import verify_password
from app.domains.integrations.models import (
    IntegrationConnection,
    IntegrationDefinition,
)
from app.domains.jobs.models import Job
from app.domains.organizations.models import Organization, OrganizationMember
from app.domains.webhooks.models import WebhookDelivery, WebhookEndpoint

from .models import EmailDelivery, FeatureFlag, PlatformAuditLog
from .schemas import (
    AdminEmailDeliveryItem,
    AdminEmailDeliveryList,
    AdminIntegrationItem,
    AdminIntegrationList,
    AdminJobItem,
    AdminJobList,
    AdminOrganizationItem,
    AdminOrganizationList,
    AdminResourceStatus,
    AdminSubscriptionChangeResponse,
    AdminSubscriptionItem,
    AdminSubscriptionList,
    AdminUserItem,
    AdminUserList,
    AdminWebhookItem,
    AdminWebhookList,
    FeatureFlagItem,
    FeatureFlagList,
)


class PlatformAdminForbidden(Exception):
    pass


class AdminResourceNotFound(Exception):
    pass


class AdminReauthenticationRequired(Exception):
    pass


class PlatformAdminService:
    def __init__(self, session: AsyncSession, actor: User) -> None:
        self.session = session
        self.actor = actor
        if actor.platform_role != "platform_admin":
            raise PlatformAdminForbidden

    async def organizations(self) -> AdminOrganizationList:
        member_count = (
            select(func.count(OrganizationMember.id))
            .where(OrganizationMember.organization_id == Organization.id)
            .correlate(Organization)
            .scalar_subquery()
        )
        rows = (
            await self.session.execute(
                select(
                    Organization,
                    member_count,
                    Plan.key,
                )
                .outerjoin(
                    OrganizationSubscription,
                    OrganizationSubscription.organization_id == Organization.id,
                )
                .outerjoin(Plan, Plan.id == OrganizationSubscription.plan_id)
                .order_by(Organization.created_at.desc())
            )
        ).all()
        return AdminOrganizationList(
            items=[
                AdminOrganizationItem(
                    id=organization.id,
                    name=organization.name,
                    slug=organization.slug,
                    status=organization.status,
                    member_count=int(count or 0),
                    plan_key=plan_key,
                    created_at=organization.created_at,
                )
                for organization, count, plan_key in rows
            ]
        )

    async def users(self) -> AdminUserList:
        users = list(
            (
                await self.session.scalars(
                    select(User).order_by(User.created_at.desc())
                )
            ).all()
        )
        return AdminUserList(
            items=[
                AdminUserItem(
                    id=user.id,
                    email=user.email_normalized,
                    display_name=user.display_name,
                    status=user.status,
                    platform_role=user.platform_role,
                    created_at=user.created_at,
                )
                for user in users
            ]
        )

    async def subscriptions(self) -> AdminSubscriptionList:
        rows = (
            await self.session.execute(
                select(OrganizationSubscription, Organization, Plan)
                .join(
                    Organization,
                    Organization.id == OrganizationSubscription.organization_id,
                )
                .join(Plan, Plan.id == OrganizationSubscription.plan_id)
                .order_by(OrganizationSubscription.created_at.desc())
            )
        ).all()
        return AdminSubscriptionList(
            items=[
                AdminSubscriptionItem(
                    id=subscription.id,
                    organization_id=organization.id,
                    organization_name=organization.name,
                    plan_key=plan.key,
                    status=subscription.status,
                    read_only=subscription.read_only,
                    trial_ends_at=subscription.trial_ends_at,
                    current_period_end=subscription.current_period_end,
                )
                for subscription, organization, plan in rows
            ]
        )

    async def feature_flags(self) -> FeatureFlagList:
        flags = list(
            (
                await self.session.scalars(
                    select(FeatureFlag).order_by(FeatureFlag.key)
                )
            ).all()
        )
        return FeatureFlagList(items=[self.feature_flag_response(flag) for flag in flags])

    async def jobs(self) -> AdminJobList:
        jobs = list(
            (
                await self.session.scalars(
                    select(Job).order_by(Job.created_at.desc()).limit(200)
                )
            ).all()
        )
        return AdminJobList(
            items=[
                AdminJobItem(
                    id=job.id,
                    organization_id=job.organization_id,
                    job_type=job.job_type,
                    status=job.status,
                    attempts=job.attempts,
                    max_attempts=job.max_attempts,
                    retryable=job.retryable,
                    error_code=job.error_code,
                    created_at=job.created_at,
                )
                for job in jobs
            ]
        )

    async def integrations(self) -> AdminIntegrationList:
        rows = (
            await self.session.execute(
                select(IntegrationConnection, IntegrationDefinition)
                .join(
                    IntegrationDefinition,
                    IntegrationDefinition.id == IntegrationConnection.definition_id,
                )
                .order_by(IntegrationConnection.created_at.desc())
                .limit(200)
            )
        ).all()
        return AdminIntegrationList(
            items=[
                AdminIntegrationItem(
                    id=connection.id,
                    organization_id=connection.organization_id,
                    definition_key=definition.key,
                    name=connection.display_name,
                    status=connection.status,
                    health_status=connection.last_health_status,
                    last_sync_at=connection.last_sync_at,
                )
                for connection, definition in rows
            ]
        )

    async def webhooks(self) -> AdminWebhookList:
        delivery_count = (
            select(func.count(WebhookDelivery.id))
            .where(WebhookDelivery.endpoint_id == WebhookEndpoint.id)
            .correlate(WebhookEndpoint)
            .scalar_subquery()
        )
        rows = (
            await self.session.execute(
                select(WebhookEndpoint, delivery_count)
                .order_by(WebhookEndpoint.created_at.desc())
                .limit(200)
            )
        ).all()
        return AdminWebhookList(
            items=[
                AdminWebhookItem(
                    id=endpoint.id,
                    organization_id=endpoint.organization_id,
                    name=endpoint.name,
                    status=endpoint.status,
                    delivery_count=int(count or 0),
                    created_at=endpoint.created_at,
                )
                for endpoint, count in rows
            ]
        )

    async def email_deliveries(self) -> AdminEmailDeliveryList:
        deliveries = list(
            (
                await self.session.scalars(
                    select(EmailDelivery)
                    .order_by(EmailDelivery.created_at.desc())
                    .limit(200)
                )
            ).all()
        )
        return AdminEmailDeliveryList(
            items=[
                AdminEmailDeliveryItem(
                    id=delivery.id,
                    organization_id=delivery.organization_id,
                    template_key=delivery.template_key,
                    recipient=delivery.recipient,
                    status=delivery.status,
                    attempts=delivery.attempts,
                    last_error=delivery.last_error,
                    created_at=delivery.created_at,
                    delivered_at=delivery.delivered_at,
                )
                for delivery in deliveries
            ]
        )

    async def suspend_organization(
        self,
        organization_id: UUID,
        *,
        reason: str,
        reauth_confirmed: bool,
        reauth_password: str,
    ) -> AdminResourceStatus:
        self._require_high_risk(reason, reauth_confirmed, reauth_password)
        organization = await self.session.get(Organization, organization_id)
        if organization is None:
            raise AdminResourceNotFound
        before = organization.status
        async with transaction(self.session):
            organization.status = "suspended"
            await self._audit(
                action="platform.organization_suspended",
                resource_type="organization",
                resource_id=organization.id,
                reason=reason,
                before={"status": before},
                after={"status": organization.status},
            )
        return AdminResourceStatus(id=organization.id, status=organization.status)

    async def ban_user(
        self,
        user_id: UUID,
        *,
        reason: str,
        reauth_confirmed: bool,
        reauth_password: str,
    ) -> AdminResourceStatus:
        self._require_high_risk(reason, reauth_confirmed, reauth_password)
        user = await self.session.get(User, user_id)
        if user is None:
            raise AdminResourceNotFound
        before = user.status
        async with transaction(self.session):
            user.status = "suspended"
            await self._audit(
                action="platform.user_suspended",
                resource_type="user",
                resource_id=user.id,
                reason=reason,
                before={"status": before},
                after={"status": user.status},
            )
        return AdminResourceStatus(id=user.id, status=user.status)

    async def replay_job(
        self,
        job_id: UUID,
        *,
        reason: str,
        reauth_confirmed: bool,
        reauth_password: str,
    ) -> Job:
        self._require_high_risk(reason, reauth_confirmed, reauth_password)
        source = await self.session.get(Job, job_id)
        if source is None:
            raise AdminResourceNotFound
        replay = Job(
            organization_id=source.organization_id,
            job_type=source.job_type,
            status="queued",
            payload_json=dict(source.payload_json),
            max_attempts=source.max_attempts,
            trace_id=source.trace_id,
        )
        async with transaction(self.session):
            self.session.add(replay)
            await self.session.flush()
            await self._audit(
                action="platform.job_replayed",
                resource_type="job",
                resource_id=replay.id,
                reason=reason,
                before={"source_job_id": str(source.id), "status": source.status},
                after={"status": replay.status},
            )
        return replay

    async def change_subscription_plan(
        self,
        subscription_id: UUID,
        *,
        target_plan: str,
        reason: str,
        reauth_confirmed: bool,
        reauth_password: str,
    ) -> AdminSubscriptionChangeResponse:
        self._require_high_risk(reason, reauth_confirmed, reauth_password)
        subscription = await self.session.get(
            OrganizationSubscription,
            subscription_id,
        )
        if subscription is None:
            raise AdminResourceNotFound
        current_plan = await self.session.get(Plan, subscription.plan_id)
        plan = await EntitlementService(self.session).ensure_plan(target_plan)
        async with transaction(self.session):
            subscription.plan_id = plan.id
            subscription.pending_plan_id = None
            subscription.pending_change_at = None
            subscription.pending_change_type = None
            await self._audit(
                action="platform.subscription_plan_changed",
                resource_type="organization_subscription",
                resource_id=subscription.id,
                reason=reason,
                before={"plan_key": current_plan.key if current_plan else None},
                after={"plan_key": plan.key},
            )
        return AdminSubscriptionChangeResponse(
            id=subscription.id,
            status=subscription.status,
            plan_key=plan.key,
        )

    async def enable_feature_flag(
        self,
        flag_id: UUID,
        *,
        rollout_percentage: int,
        reason: str,
        reauth_confirmed: bool,
        reauth_password: str,
    ) -> FeatureFlagItem:
        self._require_high_risk(reason, reauth_confirmed, reauth_password)
        flag = await self.session.get(FeatureFlag, flag_id)
        if flag is None:
            raise AdminResourceNotFound
        before = {
            "status": flag.status,
            "rollout_percentage": flag.rollout_percentage,
        }
        async with transaction(self.session):
            flag.status = "active"
            flag.rollout_percentage = rollout_percentage
            await self._audit(
                action="platform.feature_flag_enabled",
                resource_type="feature_flag",
                resource_id=flag.id,
                reason=reason,
                before=before,
                after={
                    "status": flag.status,
                    "rollout_percentage": flag.rollout_percentage,
                },
            )
        return self.feature_flag_response(flag)

    async def _audit(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: UUID,
        reason: str,
        before: dict[str, object],
        after: dict[str, object],
    ) -> None:
        self.session.add(
            PlatformAuditLog(
                actor_type="user",
                actor_user_id=self.actor.id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
                reason=reason.strip(),
                before_json=before,
                after_json=after,
                reauth_confirmed_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def feature_flag_response(flag: FeatureFlag) -> FeatureFlagItem:
        return FeatureFlagItem(
            id=flag.id,
            key=flag.key,
            description=flag.description,
            status=flag.status,
            rollout_percentage=flag.rollout_percentage,
            organization_allowlist=list(flag.organization_allowlist_json),
        )

    def _require_high_risk(
        self,
        reason: str,
        reauth_confirmed: bool,
        reauth_password: str,
    ) -> None:
        if not reauth_confirmed or not verify_password(
            reauth_password,
            self.actor.password_hash,
        ):
            raise AdminReauthenticationRequired
        if len(reason.strip()) < 5:
            raise AdminReauthenticationRequired
