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
