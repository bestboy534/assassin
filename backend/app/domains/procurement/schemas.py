from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CreatePurchaseRequest(BaseModel):
    software_name: str = Field(min_length=1, max_length=180)
    business_reason: str = Field(min_length=1)
    estimated_monthly_cost_usd: float = Field(ge=0)
    department: str = Field(min_length=1, max_length=120)
    handles_sensitive_data: bool = False
    data_categories: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_categories_for_sensitive_data(self) -> "CreatePurchaseRequest":
        if self.handles_sensitive_data and not self.data_categories:
            raise ValueError("data_categories are required when handles_sensitive_data is true")
        return self


class PurchaseRequestResponse(BaseModel):
    id: UUID
    organization_id: UUID
    software_name: str
    business_reason: str
    estimated_monthly_cost_usd: float
    department: str
    handles_sensitive_data: bool
    data_categories: list[str]
    status: str
    current_approval_task_id: UUID | None
    submitted_at: datetime | None
    decided_at: datetime | None
    created_at: datetime


class PurchaseRequestListResponse(BaseModel):
    items: list[PurchaseRequestResponse]


class ApprovalTaskResponse(BaseModel):
    id: UUID
    organization_id: UUID
    purchase_request_id: UUID
    assignee_role: str
    status: str
    created_at: datetime


class ApprovalTaskListResponse(BaseModel):
    items: list[ApprovalTaskResponse]


class ApproveTaskRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=1000)
