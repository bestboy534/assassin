from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    scopes: list[str] = Field(min_length=1, max_length=50)
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def normalize_scopes(cls, scopes: list[str]) -> list[str]:
        normalized = sorted({scope.strip().casefold() for scope in scopes if scope.strip()})
        if not normalized:
            raise ValueError("At least one API scope is required")
        return normalized


class ApiKeyResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    secret: str


class ApiKeyListResponse(BaseModel):
    items: list[ApiKeyResponse]


class ApiKeyPrincipalResponse(BaseModel):
    api_key_id: UUID
    organization_id: UUID
    name: str
    scopes: list[str]
