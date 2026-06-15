from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.identity.models import User

from .models import (
    BillingCustomer,
    BillingInvoice,
    OrganizationSubscription,
    Plan,
    PlanEntitlement,
    PlanPrice,
)
from .provider import BillingProvider, CustomerPayload
from .schemas import (
    BillingInvoiceListResponse,
    BillingInvoiceResponse,
    BillingPlanListResponse,
    BillingPlanResponse,
    BillingSummaryResponse,
    BillingUsageResponse,
    PlanEntitlementResponse,
    SubscriptionResponse,
    UsageMetricResponse,
)
from .service import PLAN_DEFINITIONS, EntitlementService
from .usage import OrganizationUsageScope, UsageService


class BillingManagementService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.entitlements = EntitlementService(session)

    async def list_plans(self) -> BillingPlanListResponse:
        plans = [
            await self.entitlements.ensure_plan(plan_key)
            for plan_key in PLAN_DEFINITIONS
        ]
        return BillingPlanListResponse(
            items=[await self._plan_response(plan) for plan in plans]
        )

    async def summary(self, organization_id: UUID) -> BillingSummaryResponse:
        subscription = await self.entitlements.ensure_default_subscription(
            organization_id
        )
        plan = await self._required_plan(subscription.plan_id)
        pending_plan = (
            await self._required_plan(subscription.pending_plan_id)
            if subscription.pending_plan_id is not None
            else None
        )
        return BillingSummaryResponse(
            plan=await self._plan_response(plan),
            pending_plan=(
                await self._plan_response(pending_plan)
                if pending_plan is not None
                else None
            ),
            subscription=self._subscription_response(subscription),
            payment_issue=subscription.status
            in {"past_due", "grace_period", "suspended"},
        )

    async def usage(self, organization_id: UUID) -> BillingUsageResponse:
        snapshots = await UsageService(self.session).snapshot(
            OrganizationUsageScope(organization_id=organization_id)
        )
        return BillingUsageResponse(
            items=[
                UsageMetricResponse(
                    metric=item.metric,
                    current_value=item.current_value,
                    limit=item.limit,
                    hard_limit=item.hard_limit,
                    status=item.status,
                )
                for item in snapshots
            ]
        )

    async def invoices(self, organization_id: UUID) -> BillingInvoiceListResponse:
        invoices = list(
            (
                await self.session.scalars(
                    select(BillingInvoice)
                    .where(BillingInvoice.organization_id == organization_id)
                    .order_by(BillingInvoice.created_at.desc())
                )
            ).all()
        )
        return BillingInvoiceListResponse(
            items=[
                BillingInvoiceResponse(
                    external_invoice_id=invoice.external_invoice_id,
                    status=invoice.status,
                    currency=invoice.currency,
                    amount_due_minor=invoice.amount_due_minor,
                    amount_paid_minor=invoice.amount_paid_minor,
                    hosted_invoice_url=invoice.hosted_invoice_url,
                    due_at=invoice.due_at,
                    paid_at=invoice.paid_at,
                    created_at=invoice.created_at,
                )
                for invoice in invoices
            ]
        )

    async def portal_session(
        self,
        organization_id: UUID,
        *,
        user: User,
        provider_name: str,
        provider: BillingProvider,
        return_url: str,
    ) -> str:
        customer = await self.session.scalar(
            select(BillingCustomer).where(
                BillingCustomer.organization_id == organization_id
            )
        )
        if customer is None:
            external = await provider.create_customer(
                CustomerPayload(
                    organization_id=organization_id,
                    email=user.email_normalized,
                    idempotency_key=f"billing-customer:{organization_id}",
                )
            )
            customer = BillingCustomer(
                organization_id=organization_id,
                provider=provider_name,
                external_customer_id=external.external_id,
                billing_email=user.email_normalized,
                status="active",
            )
            self.session.add(customer)
            await self.session.flush()
        return await provider.create_portal_session(
            customer.external_customer_id,
            return_url,
        )

    async def _plan_response(self, plan: Plan) -> BillingPlanResponse:
        price = await self.session.scalar(
            select(PlanPrice).where(
                PlanPrice.plan_id == plan.id,
                PlanPrice.currency == "USD",
                PlanPrice.billing_interval == "month",
                PlanPrice.status == "active",
            )
        )
        if price is None:
            raise RuntimeError(f"Plan {plan.key} has no active monthly price")
        entitlements = list(
            (
                await self.session.scalars(
                    select(PlanEntitlement)
                    .where(PlanEntitlement.plan_id == plan.id)
                    .order_by(PlanEntitlement.key.asc())
                )
            ).all()
        )
        return BillingPlanResponse(
            key=plan.key,
            name=plan.name,
            description=plan.description,
            currency=price.currency,
            billing_interval=price.billing_interval,
            amount_minor=price.amount_minor,
            entitlements=[
                PlanEntitlementResponse(
                    key=entitlement.key,
                    value_type=entitlement.value_type,
                    value=self._entitlement_value(entitlement),
                    hard_limit=entitlement.hard_limit,
                )
                for entitlement in entitlements
            ],
        )

    async def _required_plan(self, plan_id: UUID) -> Plan:
        plan = await self.session.get(Plan, plan_id)
        if plan is None:
            raise RuntimeError("Subscription plan is missing")
        return await self.entitlements.ensure_plan(plan.key)

    @staticmethod
    def _entitlement_value(
        entitlement: PlanEntitlement,
    ) -> bool | int | str:
        value = entitlement.value_json.get("value")
        if isinstance(value, bool | int | str):
            return value
        raise RuntimeError(f"Entitlement {entitlement.key} has an invalid value")

    @staticmethod
    def _subscription_response(
        subscription: OrganizationSubscription,
    ) -> SubscriptionResponse:
        return SubscriptionResponse(
            status=subscription.status,
            read_only=subscription.read_only,
            trial_ends_at=subscription.trial_ends_at,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            pending_change_at=subscription.pending_change_at,
            pending_change_type=subscription.pending_change_type,
        )
