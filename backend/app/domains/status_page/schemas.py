from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PublicStatusComponent(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    status: str


class PublicIncidentUpdate(BaseModel):
    id: UUID
    status: str
    message: str
    created_at: datetime


class PublicStatusIncident(BaseModel):
    id: UUID
    component_id: UUID
    component_name: str
    title: str
    summary: str
    impact: str
    status: str
    started_at: datetime
    resolved_at: datetime | None
    postmortem_summary: str | None
    updates: list[PublicIncidentUpdate]


class PublicStatusOverview(BaseModel):
    overall_status: str
    generated_at: datetime
    components: list[PublicStatusComponent]
    incidents: list[PublicStatusIncident]


class PublicIncidentList(BaseModel):
    items: list[PublicStatusIncident]


class StatusSubscriptionRequest(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class StatusSubscriptionResponse(BaseModel):
    status: str


class CreateStatusComponentRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    display_order: int = Field(default=0, ge=0, le=10_000)


class CreateStatusIncidentRequest(BaseModel):
    component_id: UUID
    title: str = Field(min_length=3, max_length=240)
    public_summary: str = Field(min_length=3, max_length=10_000)
    internal_summary: str = Field(default="", max_length=10_000)
    impact: str = Field(
        pattern="^(degraded|partial_outage|major_outage|maintenance)$"
    )
    public_message: str = Field(min_length=3, max_length=10_000)
    internal_note: str = Field(default="", max_length=10_000)


class CreateStatusIncidentUpdateRequest(BaseModel):
    status: str = Field(pattern="^(identified|monitoring|resolved)$")
    public_message: str = Field(min_length=3, max_length=10_000)
    internal_note: str = Field(default="", max_length=10_000)


class AdminStatusIncidentResponse(BaseModel):
    id: UUID
    component_id: UUID
    title: str
    public_summary: str
    internal_summary: str
    impact: str
    status: str
    started_at: datetime
    resolved_at: datetime | None
