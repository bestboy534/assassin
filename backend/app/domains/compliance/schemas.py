from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    id: UUID
    organization_id: UUID
    actor_type: str
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    ip_address: str | None
    user_agent_hash: str | None
    request_id: str | None
    before: dict[str, Any]
    after: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]


class AuditLogExportRequest(BaseModel):
    format: Literal["json"] = "json"


class AuditLogExportResponse(BaseModel):
    format: Literal["json"]
    row_count: int = Field(ge=0)
    rows: list[AuditLogResponse]
    exported_at: datetime


class CreateRetentionPolicyRequest(BaseModel):
    data_type: Literal["stored_file"]
    retention_days: int = Field(ge=1, le=3650)
    description: str = Field(default="", max_length=500)


class RetentionPolicyResponse(BaseModel):
    id: UUID
    organization_id: UUID
    data_type: str
    retention_days: int
    action: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class CreateLegalHoldRequest(BaseModel):
    resource_type: Literal["stored_file"]
    resource_id: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=2, max_length=1000)
    expires_at: datetime | None = None


class LegalHoldResponse(BaseModel):
    id: UUID
    organization_id: UUID
    resource_type: str
    resource_id: str
    reason: str
    status: str
    expires_at: datetime | None
    created_at: datetime


class DeletionPreviewResponse(BaseModel):
    data_type: str
    cutoff_at: datetime | None
    delete_candidates: list[str]
    skipped_legal_hold: list[str]


class CreateDeletionJobRequest(BaseModel):
    data_type: Literal["stored_file"]
    reauth_confirmed: bool


class DeletionJobResponse(BaseModel):
    id: UUID
    data_type: str
    status: str
    deleted_resource_ids: list[str]
    skipped_legal_hold: list[str]
    created_at: datetime
    completed_at: datetime | None
