from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .models import JobStatus


class JobResponse(BaseModel):
    id: UUID
    organization_id: UUID
    job_type: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_detail: str | None = None
    attempts: int
    max_attempts: int
    retryable: bool
    trace_id: str | None = None


class JobActionResponse(BaseModel):
    id: UUID
    status: JobStatus
