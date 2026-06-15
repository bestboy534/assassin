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
