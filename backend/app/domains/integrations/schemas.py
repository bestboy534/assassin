from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class IntegrationDefinitionResponse(BaseModel):
    id: UUID
    key: str
    name: str
    provider: str
    category: str
    auth_type: str
    capabilities: list[str]
    resource_types: list[str]
    status: str


class IntegrationDefinitionListResponse(BaseModel):
    items: list[IntegrationDefinitionResponse]


class CreateIntegrationConnectionRequest(BaseModel):
    definition_key: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=160)
    api_token: str = Field(min_length=8, max_length=500)
    sandbox_options: dict[str, Any] = Field(default_factory=dict)


class ReconnectIntegrationConnectionRequest(BaseModel):
    api_token: str = Field(min_length=8, max_length=500)


class StartOAuthRequest(BaseModel):
    redirect_uri: str = Field(min_length=8, max_length=500)


class OAuthStartResponse(BaseModel):
    authorization_url: str
    state: str
    expires_at: str


class OAuthCallbackResponse(BaseModel):
    status: Literal["authorized"]
    organization_id: UUID
    definition_key: str


class IntegrationConnectionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    definition_key: str
    definition_name: str
    display_name: str
    status: str
    auth_type: str
    credential_label: str
    credential_last4: str
    capabilities: list[str]
    resource_types: list[str]
    last_health_status: str | None
    last_sync_at: str | None
    created_at: str


class IntegrationConnectionListResponse(BaseModel):
    items: list[IntegrationConnectionResponse]


class ConnectionHealthResponse(BaseModel):
    healthy: bool
    message: str


class DeleteConnectionResponse(BaseModel):
    status: Literal["deleted"]
    data_retention: Literal["retain_synced_data"]


class SyncErrorResponse(BaseModel):
    code: str
    message: str
    external_id: str | None
    retryable: bool


class SyncRunResponse(BaseModel):
    id: UUID
    connection_id: UUID
    resource_type: str
    status: str
    cursor_before: str | None
    cursor_after: str | None
    read_count: int
    created_count: int
    updated_count: int
    skipped_count: int
    failed_count: int
    error_summary: str | None
    started_at: str
    finished_at: str | None
    errors: list[SyncErrorResponse] = Field(default_factory=list)


class SyncRunListResponse(BaseModel):
    items: list[SyncRunResponse]
