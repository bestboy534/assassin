from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

MoneyAmount = Decimal


class CreateBudgetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    fiscal_year: int = Field(ge=2000, le=2200)
    department: str = Field(min_length=1, max_length=120)
    amount: MoneyAmount = Field(gt=0, max_digits=19, decimal_places=4)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class BudgetResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    fiscal_year: int
    department: str
    amount: Decimal
    currency: str
    status: str
    created_at: datetime


class BudgetListResponse(BaseModel):
    items: list[BudgetResponse]


class CreateBudgetCommitmentRequest(BaseModel):
    commitment_type: Literal["committed", "forecast"]
    amount: MoneyAmount = Field(gt=0, max_digits=19, decimal_places=4)
    description: str = Field(min_length=1, max_length=255)


class BudgetCommitmentResponse(BaseModel):
    id: UUID
    budget_id: UUID
    commitment_type: str
    amount: Decimal
    description: str


class BudgetSummaryResponse(BaseModel):
    budget_id: UUID
    currency: str
    allocated: Decimal
    actual: Decimal
    committed: Decimal
    forecast: Decimal
    remaining: Decimal


class TransactionImportRow(BaseModel):
    external_id: str = Field(min_length=1, max_length=180)
    transaction_date: date
    merchant_name: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=500)
    amount: MoneyAmount = Field(gt=0, max_digits=19, decimal_places=4)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    department: str = Field(min_length=1, max_length=120)


class ImportTransactionsRequest(BaseModel):
    source_provider: str = Field(min_length=1, max_length=80)
    source_account_id: str = Field(min_length=1, max_length=120)
    rows: list[TransactionImportRow] = Field(min_length=1, max_length=1000)


class TransactionSplitInput(BaseModel):
    amount: MoneyAmount = Field(gt=0, max_digits=19, decimal_places=4)
    department: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=120)


class SetTransactionSplitsRequest(BaseModel):
    splits: list[TransactionSplitInput] = Field(min_length=1, max_length=50)


class TransactionSplitResponse(BaseModel):
    id: UUID
    amount: Decimal
    department: str
    category: str


class SpendTransactionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    source_provider: str
    source_account_id: str
    external_id: str
    transaction_date: date
    merchant_name: str
    description: str
    amount: Decimal
    currency: str
    department: str
    category: str | None
    application_id: UUID | None
    match_confidence: Decimal
    splits: list[TransactionSplitResponse] = Field(default_factory=list)


class TransactionListResponse(BaseModel):
    items: list[SpendTransactionResponse]


class ImportTransactionsResponse(BaseModel):
    created_count: int
    existing_count: int
    items: list[SpendTransactionResponse]


class UpdateTransactionRequest(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=120)
    department: str | None = Field(default=None, min_length=1, max_length=120)


class CreateAccountingPeriodRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_range(self) -> "CreateAccountingPeriodRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class AccountingPeriodResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    start_date: date
    end_date: date
    status: str
    locked_at: datetime | None


class AccountingPeriodListResponse(BaseModel):
    items: list[AccountingPeriodResponse]


class TransactionAnomalyResponse(BaseModel):
    id: UUID
    transaction_id: UUID
    budget_id: UUID | None
    code: str
    rule_version: str
    baseline_amount: Decimal
    observed_amount: Decimal
    status: str
    evidence: str


class TransactionAnomalyListResponse(BaseModel):
    items: list[TransactionAnomalyResponse]
