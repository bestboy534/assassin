from uuid import UUID

from pydantic import BaseModel, Field


class CreateApplicationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    category: str = Field(default="uncategorized", max_length=80)
    business_owner: str | None = Field(default=None, max_length=120)
    technical_owner: str | None = Field(default=None, max_length=120)
    approved: bool = False


class UpdateApplicationRequest(BaseModel):
    category: str | None = Field(default=None, max_length=80)
    business_owner: str | None = Field(default=None, max_length=120)
    technical_owner: str | None = Field(default=None, max_length=120)
    approved: bool | None = None
    risk_level: str | None = Field(default=None, max_length=20)


class ApplicationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    category: str
    status: str
    business_owner: str | None
    technical_owner: str | None
    risk_level: str
    approved: bool


class ApplicationListResponse(BaseModel):
    items: list[ApplicationResponse]
