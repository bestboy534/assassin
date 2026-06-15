from uuid import UUID

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=120)
    organization_name: str | None = Field(default=None, min_length=2, max_length=160)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    status: str
    platform_role: str | None


class OrganizationSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str


class AuthSessionResponse(BaseModel):
    user: UserResponse
    organizations: list[OrganizationSummary]


class AuthStatusResponse(BaseModel):
    status: str
