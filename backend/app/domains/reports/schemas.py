from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def validate_range(self) -> "DateRange":
        if self.end < self.start:
            raise ValueError("end must not be before start")
        return self


class ReportFilter(BaseModel):
    dimension: str = Field(min_length=1, max_length=80)
    operator: Literal["equals", "in"]
    value: str | list[str]


class ReportQuery(BaseModel):
    metrics: list[str] = Field(min_length=1, max_length=20)
    date_range: DateRange
    group_by: list[str] = Field(default_factory=list, max_length=4)
    filters: list[ReportFilter] = Field(default_factory=list, max_length=20)
    comparison: Literal["previous_period", "previous_year"] | None = None


class ReportMetricDefinitionResponse(BaseModel):
    key: str
    label: str
    description: str
    value_type: str
    required_permission: str
    dimensions: list[str]


class ReportMetricListResponse(BaseModel):
    items: list[ReportMetricDefinitionResponse]


class ReportDimensionResponse(BaseModel):
    key: str
    label: str


class ReportDimensionListResponse(BaseModel):
    items: list[ReportDimensionResponse]


class ReportRow(BaseModel):
    dimensions: dict[str, str]
    metrics: dict[str, Decimal]


class ReportQueryResponse(BaseModel):
    metrics: list[str]
    group_by: list[str]
    rows: list[ReportRow]
    generated_at: datetime


class CreateSavedReportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=1000)
    query: ReportQuery
    chart_type: Literal["table", "bar", "line", "area", "donut"] = "table"
    visibility: Literal["private", "organization", "role", "member"] = "private"


class SavedReportResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str
    query: dict[str, Any]
    chart_type: str
    visibility: str
    created_at: datetime
    updated_at: datetime


class SavedReportListResponse(BaseModel):
    items: list[SavedReportResponse]


class ReportSnapshotResponse(BaseModel):
    id: UUID
    saved_report_id: UUID
    payload: dict[str, Any]
    created_at: datetime


class CreateReportExportRequest(BaseModel):
    format: Literal["csv", "xlsx", "pdf"]


class ReportExportResponse(BaseModel):
    id: UUID
    job_id: UUID
    saved_report_id: UUID
    format: str
    status: str
    row_count: int
    filename: str
    download_url: str
    expires_at: datetime
    created_at: datetime


class CreateReportSubscriptionRequest(BaseModel):
    frequency: Literal["daily", "weekly", "monthly"]
    cron: str = Field(min_length=9, max_length=80)
    timezone: str = Field(min_length=1, max_length=80)
    recipients: list[str] = Field(min_length=1, max_length=50)


class ReportSubscriptionResponse(BaseModel):
    id: UUID
    saved_report_id: UUID
    frequency: str
    cron: str
    timezone: str
    recipients: list[str]
    status: str
    next_run_at: datetime
    failure_count: int
    created_at: datetime

