from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PaymentLimitsRequest(BaseModel):
    single: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    daily: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    monthly: Decimal = Field(gt=0, max_digits=19, decimal_places=4)
    total: Decimal = Field(gt=0, max_digits=19, decimal_places=4)

    @model_validator(mode="after")
    def validate_order(self) -> "PaymentLimitsRequest":
        if not self.single <= self.daily <= self.monthly <= self.total:
            raise ValueError("Limits must satisfy single <= daily <= monthly <= total")
        return self


class CreatePaymentInstrumentRequest(BaseModel):
    purchase_request_id: UUID
    owner_name: str = Field(min_length=1, max_length=120)
    merchant_lock: str = Field(min_length=1, max_length=180)
    currency: Literal["USD"]
    limits: PaymentLimitsRequest


class PaymentInstrumentResponse(BaseModel):
    id: UUID
    purchase_request_id: UUID
    provider: str
    external_id: str
    brand: str
    last4: str
    status: str
    sandbox: bool
    owner_name: str
    department: str
    merchant_lock: str
    currency: str


class PaymentLimitsResponse(BaseModel):
    single: Decimal
    daily: Decimal
    monthly: Decimal
    total: Decimal


class PaymentInstrumentBundleResponse(BaseModel):
    instrument: PaymentInstrumentResponse
    limits: PaymentLimitsResponse


class PaymentInstrumentListResponse(BaseModel):
    items: list[PaymentInstrumentBundleResponse]


class PaymentWebhookResponse(BaseModel):
    accepted: bool
    duplicate: bool
    event_id: str
