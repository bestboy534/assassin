from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ExtractInvoiceRequest(BaseModel):
    source_type: Literal["manual_text", "email", "api", "integration"]
    external_id: str = Field(min_length=1, max_length=180)
    filename: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=50000)


class InvoiceLineItemInput(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    unit_price: Decimal = Field(ge=0, max_digits=19, decimal_places=4)
    amount: Decimal = Field(ge=0, max_digits=19, decimal_places=4)
    category: str = Field(min_length=1, max_length=120)


class ConfirmInvoiceRequest(BaseModel):
    vendor_name: str = Field(min_length=1, max_length=180)
    invoice_number: str = Field(min_length=1, max_length=120)
    invoice_date: date
    due_date: date
    currency: Literal["USD"]
    subtotal: Decimal = Field(ge=0, max_digits=19, decimal_places=4)
    tax: Decimal = Field(ge=0, max_digits=19, decimal_places=4)
    total: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    purchase_order_number: str = Field(max_length=120)
    line_items: list[InvoiceLineItemInput] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dates(self) -> "ConfirmInvoiceRequest":
        if self.due_date < self.invoice_date:
            raise ValueError("Due date cannot be before invoice date")
        return self


class UpdateInvoiceRequest(BaseModel):
    subtotal: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=19,
        decimal_places=4,
    )
    tax: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=19,
        decimal_places=4,
    )
    total: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=19,
        decimal_places=4,
    )


class InvoiceResponse(BaseModel):
    id: UUID
    organization_id: UUID
    vendor_name: str
    invoice_number: str
    invoice_date: date
    due_date: date
    currency: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    purchase_order_number: str
    status: str
    exception_codes: list[str]
    duplicate_of_id: UUID | None
    current_version: int
    filename: str
    created_at: datetime


class InvoiceLineItemResponse(BaseModel):
    id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    category: str


class ExtractionResponse(BaseModel):
    provider: str
    status: str
    fields: dict[str, Any]


class InvoiceMatchResponse(BaseModel):
    id: UUID
    vendor_id: UUID | None
    contract_id: UUID | None
    transaction_id: UUID | None
    application_id: UUID | None
    purchase_request_id: UUID | None
    confidence: Decimal
    status: str
    explanation: dict[str, Any]


class AccountingExportResponse(BaseModel):
    id: UUID
    invoice_id: UUID
    provider: str
    status: str
    external_id: str | None
    external_version: int | None
    exported_invoice_version: int | None
    diff: dict[str, Any]
    attempts: int


class InvoiceBundleResponse(BaseModel):
    invoice: InvoiceResponse
    line_items: list[InvoiceLineItemResponse]
    extraction: ExtractionResponse | None
    match: InvoiceMatchResponse | None
    export: AccountingExportResponse | None


class InvoiceListResponse(BaseModel):
    items: list[InvoiceBundleResponse]


class AccountingMappingRequest(BaseModel):
    scope_type: Literal["application", "vendor", "category", "default"]
    scope_value: str = Field(min_length=1, max_length=180)
    account_code: str = Field(min_length=1, max_length=80)
    tax_code: str = Field(min_length=1, max_length=80)
    cost_center: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=120)
    project: str = Field(max_length=120)


class AccountingMappingResponse(BaseModel):
    id: UUID
    scope_type: str
    scope_value: str
    account_code: str
    tax_code: str
    cost_center: str
    department: str
    project: str


class AccountingMappingListResponse(BaseModel):
    items: list[AccountingMappingResponse]


class ResolvedAccountingMappingResponse(BaseModel):
    mapping_id: UUID
    resolved_scope_type: str
    account_code: str
    tax_code: str
    cost_center: str
    department: str
    project: str
