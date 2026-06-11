from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSavingsOpportunityRequest(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=180)
    rule_version: str = Field(min_length=1, max_length=80)
    period_key: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=220)
    department: str = Field(min_length=1, max_length=120)
    category: Literal[
        "cancellation",
        "downgrade",
        "negotiation",
        "seat_recovery",
        "cost_avoidance",
    ]
    monthly_baseline: Decimal = Field(ge=0, max_digits=19, decimal_places=4)
    currency: Literal["USD"]
    effective_date: date
    contract_end: date | None = None
    evidence: str = Field(min_length=1, max_length=2000)


class SavingsBaselineResponse(BaseModel):
    id: UUID
    version: int
    monthly_cost: Decimal
    calculation_months: int
    amount: Decimal
    calculation_method: str
    effective_date: date
    contract_end: date | None


class SavingsOpportunityResponse(BaseModel):
    id: UUID
    organization_id: UUID
    source_type: str
    source_id: str
    rule_version: str
    period_key: str
    title: str
    department: str
    category: str
    status: str
    estimated_amount: Decimal
    currency: str
    evidence: str
    created_at: datetime
    baseline: SavingsBaselineResponse


class SavingsOpportunityListResponse(BaseModel):
    items: list[SavingsOpportunityResponse]


class CreateOptimizationProjectRequest(BaseModel):
    owner_name: str = Field(min_length=1, max_length=120)
    due_date: date


class OptimizationTaskResponse(BaseModel):
    id: UUID
    title: str
    status: str


class OptimizationProjectResponse(BaseModel):
    id: UUID
    opportunity_id: UUID
    owner_name: str
    due_date: date
    status: str
    target_amount: Decimal
    currency: str


class SavingsResultResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    action: str
    effective_date: date
    new_monthly_cost: Decimal
    realized_amount: Decimal
    verified_amount: Decimal
    realization_evidence: str
    evidence_references: list[str]
    verified_at: datetime | None


class OptimizationProjectBundleResponse(BaseModel):
    project: OptimizationProjectResponse
    tasks: list[OptimizationTaskResponse]
    result: SavingsResultResponse | None


class OptimizationProjectListResponse(BaseModel):
    items: list[OptimizationProjectBundleResponse]


class RealizeSavingsRequest(BaseModel):
    action: Literal["cancelled", "downgraded", "negotiated", "seats_recovered"]
    effective_date: date
    new_monthly_cost: Decimal = Field(ge=0, max_digits=19, decimal_places=4)
    evidence: str = Field(min_length=1, max_length=2000)


class VerifySavingsRequest(BaseModel):
    evidence_references: list[str] = Field(min_length=1, max_length=50)


class SavingsSummaryResponse(BaseModel):
    currency: str
    estimated: Decimal
    realized: Decimal
    verified: Decimal
    cost_avoidance: Decimal
