from decimal import Decimal

import pytest

from app.domains.accounting.adapters import (
    BillPayload,
    FakeAccountingProvider,
    FakeInvoiceExtractor,
)


@pytest.mark.asyncio
async def test_fake_extractor_preserves_confidence_and_evidence() -> None:
    result = await FakeInvoiceExtractor().extract(
        """
        vendor: Notion Labs
        invoice_number: INV-2026-001
        invoice_date: 2026-07-10
        due_date: 2026-08-09
        currency: USD
        subtotal: 100.00
        tax: 18.00
        total: 118.00
        line: Notion enterprise subscription | 1 | 118.00
        """
    )

    assert result.fields["total"].value == "118.00"
    assert result.fields["total"].confidence == Decimal("0.9900")
    assert result.fields["total"].evidence.page == 1
    assert result.fields["total"].evidence.line > 0


@pytest.mark.asyncio
async def test_fake_accounting_provider_is_idempotent() -> None:
    provider = FakeAccountingProvider()
    payload = BillPayload(
        vendor_name="Notion Labs",
        invoice_number="INV-2026-001",
        invoice_date="2026-07-10",
        due_date="2026-08-09",
        currency="USD",
        total="118.0000",
        account_code="6200",
        tax_code="VAT18",
        department="Operations",
        external_version=1,
    )

    first = await provider.upsert_bill(payload, "invoice-export-001")
    second = await provider.upsert_bill(payload, "invoice-export-001")

    assert first.external_id == second.external_id
    assert first.external_version == second.external_version
