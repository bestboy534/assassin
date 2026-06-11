from uuid import UUID

from pydantic import BaseModel, Field


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str


class OrganizationListResponse(BaseModel):
    items: list[OrganizationResponse]
