from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateFrameworkRequest(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=2000)


class FrameworkResponse(BaseModel):
    id: UUID
    organization_id: UUID
    code: str
    name: str
    version: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class FrameworkListResponse(BaseModel):
    items: list[FrameworkResponse]


class CreateControlRequest(BaseModel):
    code: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=3000)
    frequency_days: int = Field(default=90, ge=1, le=3650)


class AssignControlOwnerRequest(BaseModel):
    user_id: UUID
    role: Literal["owner", "reviewer"] = "owner"


class ControlOwnerResponse(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    created_at: datetime


class CreateEvidenceRequest(BaseModel):
    stored_file_id: UUID
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=2000)
    collected_at: datetime | None = None
    expires_at: datetime | None = None


class ControlEvidenceResponse(BaseModel):
    id: UUID
    stored_file_id: UUID
    title: str
    description: str
    status: str
    collected_at: datetime
    expires_at: datetime | None
    created_at: datetime


class CreateControlReviewRequest(BaseModel):
    outcome: Literal["effective", "ineffective", "needs_attention"]
    notes: str = Field(default="", max_length=3000)


class ControlReviewResponse(BaseModel):
    id: UUID
    reviewer_user_id: UUID
    outcome: str
    notes: str
    reviewed_at: datetime
    next_review_at: datetime | None
    created_at: datetime


class ComplianceControlResponse(BaseModel):
    id: UUID
    organization_id: UUID
    framework_id: UUID
    code: str
    title: str
    description: str
    status: str
    frequency_days: int
    last_reviewed_at: datetime | None
    next_review_at: datetime | None
    owners: list[ControlOwnerResponse]
    evidence: list[ControlEvidenceResponse]
    reviews: list[ControlReviewResponse]
    created_at: datetime
    updated_at: datetime


class EvidenceDownloadResponse(BaseModel):
    id: UUID
    download_url: str
    expires_in: int


class CreateSecurityIncidentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    severity: Literal["low", "medium", "high", "critical"]
    summary: str = Field(min_length=1, max_length=4000)
    detected_at: datetime


class CreateIncidentTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    assignee_user_id: UUID | None = None
    due_at: datetime | None = None


class UpdateIncidentTaskRequest(BaseModel):
    status: Literal["open", "in_progress", "completed", "cancelled"]


class IncidentTaskResponse(BaseModel):
    id: UUID
    title: str
    status: str
    assignee_user_id: UUID | None
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SecurityIncidentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    severity: str
    status: str
    summary: str
    detected_at: datetime
    resolved_at: datetime | None
    tasks: list[IncidentTaskResponse]
    created_at: datetime
    updated_at: datetime


class SecurityIncidentListResponse(BaseModel):
    items: list[SecurityIncidentResponse]
