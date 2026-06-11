from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CreateVendorRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    domain: str | None = Field(default=None, max_length=255)
    country_code: str | None = Field(default=None, max_length=8)
    category: str = Field(min_length=1, max_length=120)
    business_owner: str | None = Field(default=None, max_length=120)
    risk_owner: str | None = Field(default=None, max_length=120)


class VendorResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    domain: str | None
    country_code: str | None
    category: str
    status: str
    business_owner: str | None
    risk_owner: str | None
    overall_risk_score: int | None
    risk_level: str
    created_at: datetime


class VendorListResponse(BaseModel):
    items: list[VendorResponse]


class CreateVendorAliasRequest(BaseModel):
    alias: str = Field(min_length=1, max_length=255)


class VendorAliasResponse(BaseModel):
    id: UUID
    vendor_id: UUID
    alias: str


class CreateVendorAssessmentRequest(BaseModel):
    questionnaire_version: int = Field(ge=1)
    has_soc2: bool
    has_iso27001: bool
    has_dpa: bool
    supports_sso: bool
    has_incident_response: bool
    financial_stability: Literal["strong", "medium", "weak"]
    service_criticality: Literal["low", "medium", "high"]
    stores_sensitive_data: bool


class RiskDimensionResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    reasons: list[str]


class VendorAssessmentResponse(BaseModel):
    id: UUID
    vendor_id: UUID
    questionnaire_version: int
    rule_version: str
    status: str
    total_score: int
    dimensions: dict[str, RiskDimensionResponse]
    submitted_at: datetime


class RiskFindingResponse(BaseModel):
    id: UUID
    vendor_id: UUID
    assessment_id: UUID
    dimension: str
    title: str
    description: str
    severity: str
    status: str
    owner_name: str
    due_date: date
    mitigation_plan: str | None
    accepted_reason: str | None
    accepted_until: date | None


class VendorAssessmentBundleResponse(BaseModel):
    assessment: VendorAssessmentResponse
    findings: list[RiskFindingResponse]


class LatestVendorAssessmentResponse(BaseModel):
    item: VendorAssessmentBundleResponse | None


class RiskFindingListResponse(BaseModel):
    items: list[RiskFindingResponse]


class AcceptRiskFindingRequest(BaseModel):
    reason: str = Field(min_length=8, max_length=2000)
    expires_at: date
    risk_owner: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_expiry(self) -> "AcceptRiskFindingRequest":
        if self.expires_at <= date.today():
            raise ValueError("expires_at must be in the future")
        return self
