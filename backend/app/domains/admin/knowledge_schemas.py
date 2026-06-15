from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .schemas import HighRiskActionRequest


class CreateKnowledgeEntryRequest(BaseModel):
    key: str = Field(min_length=2, max_length=160, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    data: dict[str, Any]
    change_summary: str = Field(min_length=3, max_length=1000)


class CreateKnowledgeDraftRequest(BaseModel):
    data: dict[str, Any]
    change_summary: str = Field(min_length=3, max_length=1000)


class RollbackKnowledgeRequest(HighRiskActionRequest):
    target_version: int = Field(ge=1)


class KnowledgeEntryResponse(BaseModel):
    id: UUID
    object_type: str
    key: str
    status: str
    published_version_number: int | None
    created_at: datetime


class KnowledgeVersionResponse(BaseModel):
    id: UUID
    entry_id: UUID
    version_number: int
    status: str
    data: dict[str, Any]
    change_summary: str
    created_by_user_id: UUID
    reviewed_by_user_id: UUID | None
    published_by_user_id: UUID | None
    created_at: datetime
    reviewed_at: datetime | None
    published_at: datetime | None


class KnowledgeBundleResponse(BaseModel):
    entry: KnowledgeEntryResponse
    version: KnowledgeVersionResponse


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeBundleResponse]


class PublicKnowledgeResponse(BaseModel):
    key: str
    object_type: str
    version_number: int
    data: dict[str, Any]
    published_at: datetime
