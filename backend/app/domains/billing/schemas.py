from datetime import datetime

from pydantic import BaseModel, Field


class BillingWebhookResponse(BaseModel):
    accepted: bool
    duplicate: bool
    stale: bool
    event_id: str


class PlanEntitlementResponse(BaseModel):
    key: str
    value_type: str
    value: bool | int | str
    hard_limit: bool


class BillingPlanResponse(BaseModel):
    key: str
    name: str
    description: str
    currency: str
    billing_interval: str
    amount_minor: int
    entitlements: list[PlanEntitlementResponse]


class BillingPlanListResponse(BaseModel):
    items: list[BillingPlanResponse]


class SubscriptionResponse(BaseModel):
    status: str
    read_only: bool
    trial_ends_at: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    pending_change_at: datetime | None
    pending_change_type: str | None


class BillingSummaryResponse(BaseModel):
    plan: BillingPlanResponse
    subscription: SubscriptionResponse
    pending_plan: BillingPlanResponse | None = None
    payment_issue: bool = False


class UsageMetricResponse(BaseModel):
    metric: str
    current_value: int
    limit: int
    hard_limit: bool
    status: str


class BillingUsageResponse(BaseModel):
    items: list[UsageMetricResponse]


class BillingInvoiceResponse(BaseModel):
    external_invoice_id: str
    status: str
    currency: str
    amount_due_minor: int
    amount_paid_minor: int
    hosted_invoice_url: str | None
    due_at: datetime | None
    paid_at: datetime | None
    created_at: datetime


class BillingInvoiceListResponse(BaseModel):
    items: list[BillingInvoiceResponse]


class PlanChangeRequest(BaseModel):
    target_plan: str = Field(min_length=1, max_length=80)


class PlanChangePreviewResponse(BaseModel):
    current_plan: str
    target_plan: str
    direction: str
    effective_at: datetime
    current_amount_minor: int
    target_amount_minor: int
    proration_minor: int
    lost_features: list[str]
    over_limit: dict[str, int]


class PortalSessionRequest(BaseModel):
    return_url: str = Field(min_length=1, max_length=1000)


class PortalSessionResponse(BaseModel):
    url: str
