from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas import SourceType, SubscriptionItem


class CreateAnalysisRunRequest(BaseModel):
    raw_text: str = Field(min_length=1)
    source_hint: SourceType = "unknown"


class AnalysisRunResponse(BaseModel):
    id: str
    organization_id: UUID | None
    status: str
    source_hint: SourceType
    items_count: int
    total_monthly_cost_usd: float
    created_at: datetime


class AnalysisRunListResponse(BaseModel):
    items: list[AnalysisRunResponse]


class AnalysisRunDetailResponse(BaseModel):
    run: AnalysisRunResponse
    items: list[SubscriptionItem]
