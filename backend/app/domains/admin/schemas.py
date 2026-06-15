from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminOrganizationItem(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str
    member_count: int
    plan_key: str | None
    created_at: datetime


class AdminUserItem(BaseModel):
    id: UUID
    email: str
    display_name: str
    status: str
    platform_role: str | None
    created_at: datetime


class AdminSubscriptionItem(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: str
    plan_key: str
    status: str
    read_only: bool
    trial_ends_at: datetime | None
    current_period_end: datetime | None


class FeatureFlagItem(BaseModel):
    id: UUID
    key: str
    description: str
    status: str
    rollout_percentage: int
    organization_allowlist: list[str]


class AdminJobItem(BaseModel):
    id: UUID
    organization_id: UUID
    job_type: str
    status: str
    attempts: int
    max_attempts: int
    retryable: bool
    error_code: str | None
    created_at: datetime


class AdminIntegrationItem(BaseModel):
    id: UUID
    organization_id: UUID
    definition_key: str
    name: str
    status: str
    health_status: str | None
    last_sync_at: datetime | None


class AdminWebhookItem(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    status: str
    delivery_count: int
    created_at: datetime


class AdminEmailDeliveryItem(BaseModel):
    id: UUID
    organization_id: UUID | None
    template_key: str
    recipient: str
    status: str
    attempts: int
    last_error: str | None
    created_at: datetime
    delivered_at: datetime | None


class AdminItemsResponse(BaseModel):
    items: list[dict[str, object]]


class AdminResourceStatus(BaseModel):
    id: UUID
    status: str


class AdminSubscriptionChangeResponse(AdminResourceStatus):
    plan_key: str


class HighRiskActionRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)
    reauth_confirmed: bool
    reauth_password: str = Field(min_length=8, max_length=256)


class ChangeSubscriptionPlanRequest(HighRiskActionRequest):
    target_plan: str = Field(min_length=2, max_length=80)


class EnableFeatureFlagRequest(HighRiskActionRequest):
    rollout_percentage: int = Field(ge=0, le=100)


class AdminOrganizationList(BaseModel):
    items: list[AdminOrganizationItem]


class AdminUserList(BaseModel):
    items: list[AdminUserItem]


class AdminSubscriptionList(BaseModel):
    items: list[AdminSubscriptionItem]


class FeatureFlagList(BaseModel):
    items: list[FeatureFlagItem]


class AdminJobList(BaseModel):
    items: list[AdminJobItem]


class AdminIntegrationList(BaseModel):
    items: list[AdminIntegrationItem]


class AdminWebhookList(BaseModel):
    items: list[AdminWebhookItem]


class AdminEmailDeliveryList(BaseModel):
    items: list[AdminEmailDeliveryItem]
