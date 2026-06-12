from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CreateContractRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    vendor_name: str = Field(min_length=1, max_length=180)
    application_name: str | None = Field(default=None, max_length=180)
    owner_name: str = Field(min_length=1, max_length=120)
    start_date: date
    end_date: date
    amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=8)
    billing_frequency: str = Field(min_length=1, max_length=32)
    auto_renew: bool = False
    notice_period_days: int = Field(default=0, ge=0, le=730)

    @model_validator(mode="after")
    def validate_date_range(self) -> "CreateContractRequest":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class UpdateContractVersionRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    billing_frequency: str | None = Field(default=None, min_length=1, max_length=32)
    auto_renew: bool | None = None
    notice_period_days: int | None = Field(default=None, ge=0, le=730)


class ContractResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    vendor_name: str
    application_name: str | None
    owner_name: str
    status: str
    current_version_id: UUID | None
    created_at: datetime


class ContractVersionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    contract_id: UUID
    version_number: int
    status: str
    start_date: date
    end_date: date
    amount: float
    currency: str
    billing_frequency: str
    auto_renew: bool
    notice_period_days: int
    signed_at: datetime | None


class RenewalResponse(BaseModel):
    id: UUID
    organization_id: UUID
    contract_id: UUID
    source_version_id: UUID
    renewal_date: date
    decision_deadline: date
    owner_name: str
    status: str
    decision: str | None
    current_amount: float
    currency: str


class ContractBundleResponse(BaseModel):
    contract: ContractResponse
    version: ContractVersionResponse
    renewal: RenewalResponse | None = None


class ContractListResponse(BaseModel):
    items: list[ContractResponse]


class RenewalListResponse(BaseModel):
    items: list[RenewalResponse]
