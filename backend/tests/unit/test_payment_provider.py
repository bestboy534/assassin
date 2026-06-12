import hashlib
import hmac
import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domains.payments.provider import (
    CreateInstrument,
    FakePaymentProvider,
    InvalidPaymentWebhook,
    PaymentLimits,
)


@pytest.mark.asyncio
async def test_fake_payment_provider_contract() -> None:
    provider = FakePaymentProvider(webhook_secret="provider-contract-secret")
    instrument = await provider.create_instrument(
        CreateInstrument(
            idempotency_key="create-notion-card",
            owner_name="运营负责人",
            merchant_lock="Notion Labs",
            currency="USD",
            limits=PaymentLimits(
                single=Decimal("300.00"),
                daily=Decimal("500.00"),
                monthly=Decimal("1200.00"),
                total=Decimal("12000.00"),
            ),
        )
    )

    assert instrument.external_id.startswith("sandbox_")
    assert instrument.last4 == "4242"
    assert instrument.status == "active"
    assert instrument.sandbox is True

    frozen = await provider.freeze(instrument.external_id)
    assert frozen.status == "pending"

    body = json.dumps(
        {
            "event_id": "evt-provider-contract",
            "type": "instrument.frozen",
            "external_id": instrument.external_id,
        },
        separators=(",", ":"),
    ).encode()
    timestamp = str(int(datetime.now(UTC).timestamp()))
    signature = hmac.new(
        b"provider-contract-secret",
        timestamp.encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    event = provider.verify_webhook(
        {
            "x-payment-timestamp": timestamp,
            "x-payment-signature": signature,
        },
        body,
    )
    assert event.event_id == "evt-provider-contract"
    assert event.event_type == "instrument.frozen"

    with pytest.raises(InvalidPaymentWebhook):
        provider.verify_webhook(
            {
                "x-payment-timestamp": timestamp,
                "x-payment-signature": "invalid",
            },
            body,
        )
