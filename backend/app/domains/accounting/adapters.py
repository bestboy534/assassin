import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class FieldEvidence:
    page: int
    line: int
    text: str


@dataclass(frozen=True)
class ExtractedField:
    value: str
    confidence: Decimal
    evidence: FieldEvidence


@dataclass(frozen=True)
class ExtractedLineItem:
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


@dataclass(frozen=True)
class InvoiceExtractionResult:
    fields: dict[str, ExtractedField]
    line_items: list[ExtractedLineItem]


class InvoiceExtractor(Protocol):
    async def extract(self, text: str) -> InvoiceExtractionResult: ...


class FakeInvoiceExtractor:
    async def extract(self, text: str) -> InvoiceExtractionResult:
        fields: dict[str, ExtractedField] = {}
        line_items: list[ExtractedLineItem] = []
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            key = key.strip().lower()
            value = raw_value.strip()
            if key == "line":
                parts = [part.strip() for part in value.split("|")]
                if len(parts) == 3:
                    line_items.append(
                        ExtractedLineItem(
                            description=parts[0],
                            quantity=Decimal(parts[1]),
                            unit_price=Decimal(parts[2]),
                            amount=Decimal(parts[1]) * Decimal(parts[2]),
                        )
                    )
                continue
            fields[key] = ExtractedField(
                value=value,
                confidence=Decimal("0.9900"),
                evidence=FieldEvidence(
                    page=1,
                    line=line_number,
                    text=line,
                ),
            )
        return InvoiceExtractionResult(fields=fields, line_items=line_items)


@dataclass(frozen=True)
class BillPayload:
    vendor_name: str
    invoice_number: str
    invoice_date: str
    due_date: str
    currency: str
    total: str
    account_code: str
    tax_code: str
    department: str
    external_version: int


@dataclass(frozen=True)
class ExternalBill:
    external_id: str
    external_version: int


class AccountingProvider(Protocol):
    async def upsert_bill(
        self,
        payload: BillPayload,
        idempotency_key: str,
    ) -> ExternalBill: ...


class FakeAccountingProvider:
    async def upsert_bill(
        self,
        payload: BillPayload,
        idempotency_key: str,
    ) -> ExternalBill:
        digest = hashlib.sha256(idempotency_key.encode()).hexdigest()[:20]
        return ExternalBill(
            external_id=f"sandbox_bill_{digest}",
            external_version=payload.external_version,
        )


def build_invoice_extractor() -> InvoiceExtractor:
    return FakeInvoiceExtractor()


def build_accounting_provider() -> AccountingProvider:
    return FakeAccountingProvider()
