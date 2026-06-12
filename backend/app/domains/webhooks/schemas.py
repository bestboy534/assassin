from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateWebhookEndpointRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=1, max_length=1000)
    events: list[str] = Field(min_length=1, max_length=100)

    @field_validator("url")
    @classmethod
    def require_https(cls, url: str) -> str:
        normalized = url.strip()
        if not normalized.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")
        return normalized

    @field_validator("events")
    @classmethod
    def normalize_events(cls, events: list[str]) -> list[str]:
        normalized = sorted({event.strip().casefold() for event in events if event.strip()})
        if not normalized:
            raise ValueError("At least one webhook event is required")
        return normalized


class RotateWebhookSecretRequest(BaseModel):
    overlap_seconds: int = Field(default=3600, ge=60, le=86400)


class TestWebhookRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)


class WebhookEndpointResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    url: str
    events: list[str]
    status: str
    secret_version: int
    previous_secret_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WebhookEndpointCreatedResponse(WebhookEndpointResponse):
    secret: str


class WebhookEndpointListResponse(BaseModel):
    items: list[WebhookEndpointResponse]


class WebhookSecretRotatedResponse(BaseModel):
    id: UUID
    secret: str
    secret_version: int
    previous_secret_expires_at: datetime


class WebhookDeliveryResponse(BaseModel):
    id: UUID
    endpoint_id: UUID
    event_id: UUID
    event_type: str
    status: str
    attempts: int
    next_attempt_at: datetime
    response_status: int | None
    last_error: str | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryListResponse(BaseModel):
    items: list[WebhookDeliveryResponse]
