from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSupportTicketRequest(BaseModel):
    organization_id: UUID
    subject: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=3, max_length=10_000)
    category: str = Field(min_length=2, max_length=60)
    priority: str = Field(pattern="^(low|normal|high|urgent)$")


class UpdateSupportTicketRequest(BaseModel):
    status: str = Field(
        pattern="^(new|open|waiting_customer|waiting_support|resolved|closed)$"
    )


class ResolveSupportTicketRequest(BaseModel):
    resolution: str = Field(min_length=3, max_length=10_000)


class CreateSupportMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)


class SupportTicketResponse(BaseModel):
    id: UUID
    organization_id: UUID
    subject: str
    description: str
    category: str
    priority: str
    status: str
    support_tier: str
    resolution_summary: str | None
    first_response_due_at: datetime
    resolution_due_at: datetime
    first_responded_at: datetime | None
    sla_paused_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SupportTicketListResponse(BaseModel):
    items: list[SupportTicketResponse]


class SupportMessageResponse(BaseModel):
    id: UUID
    support_ticket_id: UUID
    author_type: str
    body: str
    internal: bool
    created_at: datetime


class SupportMessageListResponse(BaseModel):
    items: list[SupportMessageResponse]


class SupportAgentResponse(BaseModel):
    id: UUID
    display_name: str
    platform_role: str


class SupportAgentListResponse(BaseModel):
    items: list[SupportAgentResponse]


class CreateSupportSatisfactionRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class SupportSatisfactionResponse(BaseModel):
    id: UUID
    support_ticket_id: UUID
    rating: int
    comment: str
    created_at: datetime


class CreateSupportGrantRequest(BaseModel):
    support_user_id: UUID
    scopes: list[str] = Field(min_length=1, max_length=4)
    reason: str = Field(min_length=3, max_length=1000)
    expires_at: datetime


class SupportGrantResponse(BaseModel):
    id: UUID
    organization_id: UUID
    support_user_id: UUID
    scopes: list[str]
    reason: str
    approved_by_user_id: UUID
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime


class SupportGrantListResponse(BaseModel):
    items: list[SupportGrantResponse]


class DiagnosticAccessRequest(BaseModel):
    purpose: str = Field(min_length=3, max_length=1000)


class SyncDiagnosticItem(BaseModel):
    id: UUID
    connection_id: UUID
    resource_type: str
    status: str
    read_count: int
    created_count: int
    updated_count: int
    failed_count: int
    attempts: int
    error_summary: str | None
    started_at: datetime
    finished_at: datetime | None


class SupportDiagnosticResponse(BaseModel):
    grant_id: UUID
    organization_id: UUID
    items: list[SyncDiagnosticItem]
