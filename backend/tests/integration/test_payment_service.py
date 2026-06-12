from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.database import Database
from app.domains.identity.models import User
from app.domains.organizations.service import OrganizationContext
from app.domains.payments.models import PaymentRequest
from app.domains.payments.provider import (
    CreateInstrument,
    FakePaymentProvider,
    ProviderInstrument,
)
from app.domains.payments.schemas import (
    CreatePaymentInstrumentRequest,
    PaymentLimitsRequest,
)
from app.domains.payments.service import PaymentService
from app.domains.procurement.models import PurchaseRequest


class FailsOncePaymentProvider(FakePaymentProvider):
    def __init__(self) -> None:
        super().__init__("test-payment-webhook-secret")
        self.failed = False

    async def create_instrument(
        self,
        request: CreateInstrument,
    ) -> ProviderInstrument:
        if not self.failed:
            self.failed = True
            raise RuntimeError("provider timeout")
        return await super().create_instrument(request)


@pytest.mark.asyncio
async def test_failed_creation_intent_can_be_retried(
    database: Database,
) -> None:
    async with database.session_factory() as session:
        user = User(
            id=uuid4(),
            email_normalized="payments@example.com",
            display_name="Payment owner",
            password_hash="not-used",
            status="active",
        )
        purchase = PurchaseRequest(
            id=uuid4(),
            organization_id=uuid4(),
            created_by_user_id=user.id,
            software_name="Notion",
            business_reason="Knowledge management",
            estimated_monthly_cost_usd=120,
            department="Operations",
            handles_sensitive_data=False,
            data_categories_json="[]",
            status="approved",
        )
        session.add_all([user, purchase])
        await session.commit()

        context = OrganizationContext(
            organization_id=purchase.organization_id,
            user_id=user.id,
            membership_id=uuid4(),
            role="owner",
        )
        body = CreatePaymentInstrumentRequest(
            purchase_request_id=purchase.id,
            owner_name="Payment owner",
            merchant_lock="Notion Labs",
            currency="USD",
            limits=PaymentLimitsRequest(
                single=Decimal("300"),
                daily=Decimal("500"),
                monthly=Decimal("1200"),
                total=Decimal("12000"),
            ),
        )
        service = PaymentService(
            session,
            FailsOncePaymentProvider(),
            "fake",
        )

        with pytest.raises(RuntimeError, match="provider timeout"):
            await service.create_instrument(
                context,
                user,
                body,
                "card-notion-retry",
            )

        failed_request = await session.scalar(select(PaymentRequest))
        assert failed_request is not None
        assert failed_request.status == "failed"

        created = await service.create_instrument(
            context,
            user,
            body,
            "card-notion-retry",
        )

        assert created.instrument.status == "active"
        assert failed_request.status == "completed"
