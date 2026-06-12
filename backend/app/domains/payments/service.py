import json
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.money import quantize_money
from app.core.transactions import transaction
from app.domains.identity.models import User
from app.domains.organizations.service import OrganizationContext
from app.domains.procurement.models import PurchaseRequest
from app.domains.spend.models import SpendTransaction

from .models import (
    PaymentAction,
    PaymentEvent,
    PaymentInstrument,
    PaymentLimit,
    PaymentRequest,
)
from .provider import (
    CreateInstrument,
    PaymentLimits,
    PaymentProvider,
    ProviderEvent,
)
from .schemas import (
    CreatePaymentInstrumentRequest,
    PaymentInstrumentBundleResponse,
    PaymentInstrumentListResponse,
    PaymentInstrumentResponse,
    PaymentLimitsRequest,
    PaymentLimitsResponse,
    PaymentWebhookResponse,
)


class PurchaseNotApproved(Exception):
    pass


class PaymentInstrumentNotFound(Exception):
    pass


class InvalidPaymentTransition(Exception):
    pass


class PaymentRequestConflict(Exception):
    pass


def provider_limits(body: PaymentLimitsRequest) -> PaymentLimits:
    return PaymentLimits(
        single=quantize_money(body.single),
        daily=quantize_money(body.daily),
        monthly=quantize_money(body.monthly),
        total=quantize_money(body.total),
    )


def instrument_response(item: PaymentInstrument) -> PaymentInstrumentResponse:
    return PaymentInstrumentResponse(
        id=item.id,
        purchase_request_id=item.payment_request.purchase_request_id,
        provider=item.provider,
        external_id=item.external_id,
        brand=item.brand,
        last4=item.last4,
        status=item.status,
        sandbox=item.sandbox,
        owner_name=item.owner_name,
        department=item.department,
        merchant_lock=item.merchant_lock,
        currency=item.currency,
    )


def limits_response(item: PaymentLimit) -> PaymentLimitsResponse:
    return PaymentLimitsResponse(
        single=quantize_money(item.single_amount),
        daily=quantize_money(item.daily_amount),
        monthly=quantize_money(item.monthly_amount),
        total=quantize_money(item.total_amount),
    )


def bundle_response(item: PaymentInstrument) -> PaymentInstrumentBundleResponse:
    return PaymentInstrumentBundleResponse(
        instrument=instrument_response(item),
        limits=limits_response(item.limits),
    )


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        provider: PaymentProvider,
        provider_name: str,
    ) -> None:
        self.session = session
        self.provider = provider
        self.provider_name = provider_name

    async def create_instrument(
        self,
        context: OrganizationContext,
        user: User,
        body: CreatePaymentInstrumentRequest,
        idempotency_key: str,
    ) -> PaymentInstrumentBundleResponse:
        existing_request = await self.session.scalar(
            select(PaymentRequest)
            .where(
                PaymentRequest.purchase_request_id == body.purchase_request_id,
                PaymentRequest.organization_id == context.organization_id,
            )
            .options(
                selectinload(PaymentRequest.instrument).selectinload(
                    PaymentInstrument.limits
                ),
                selectinload(PaymentRequest.instrument).selectinload(
                    PaymentInstrument.payment_request
                ),
            )
        )
        if existing_request is not None and existing_request.instrument is not None:
            return bundle_response(existing_request.instrument)

        purchase = await self.session.scalar(
            select(PurchaseRequest).where(
                PurchaseRequest.id == body.purchase_request_id,
                PurchaseRequest.organization_id == context.organization_id,
            )
        )
        if purchase is None or purchase.status != "approved":
            raise PurchaseNotApproved

        if existing_request is not None:
            if (
                existing_request.status != "failed"
                or existing_request.idempotency_key != idempotency_key
            ):
                raise PaymentRequestConflict
            payment_request = existing_request
            payment_request.requested_by_user_id = user.id
            payment_request.status = "creating"
        else:
            payment_request = PaymentRequest(
                organization_id=context.organization_id,
                purchase_request_id=purchase.id,
                requested_by_user_id=user.id,
                provider=self.provider_name,
                idempotency_key=idempotency_key,
                status="creating",
            )
            self.session.add(payment_request)
        await self.session.commit()

        limits = provider_limits(body.limits)
        try:
            provider_instrument = await self.provider.create_instrument(
                CreateInstrument(
                    idempotency_key=idempotency_key,
                    owner_name=body.owner_name.strip(),
                    merchant_lock=body.merchant_lock.strip(),
                    currency=body.currency,
                    limits=limits,
                )
            )
        except Exception:
            payment_request.status = "failed"
            await self.session.commit()
            raise

        instrument = PaymentInstrument(
            organization_id=context.organization_id,
            provider=self.provider_name,
            external_id=provider_instrument.external_id,
            brand=provider_instrument.brand,
            last4=provider_instrument.last4,
            status=provider_instrument.status,
            sandbox=provider_instrument.sandbox,
            owner_name=body.owner_name.strip(),
            department=purchase.department,
            merchant_lock=body.merchant_lock.strip(),
            currency=body.currency,
        )
        instrument.limits = PaymentLimit(
            organization_id=context.organization_id,
            single_amount=limits.single,
            daily_amount=limits.daily,
            monthly_amount=limits.monthly,
            total_amount=limits.total,
        )
        instrument.actions.append(
            PaymentAction(
                organization_id=context.organization_id,
                requested_by_user_id=user.id,
                action="create",
                status="confirmed",
                details_json=json.dumps(
                    {"purchase_request_id": str(purchase.id)},
                    ensure_ascii=False,
                ),
            )
        )
        payment_request.instrument = instrument
        payment_request.status = "completed"
        await self.session.flush()
        await self.session.commit()
        return bundle_response(instrument)

    async def list_instruments(
        self,
        context: OrganizationContext,
    ) -> PaymentInstrumentListResponse:
        items = (
            await self.session.scalars(
                select(PaymentInstrument)
                .where(PaymentInstrument.organization_id == context.organization_id)
                .options(
                    selectinload(PaymentInstrument.limits),
                    selectinload(PaymentInstrument.payment_request),
                )
                .order_by(PaymentInstrument.created_at.desc())
            )
        ).all()
        return PaymentInstrumentListResponse(
            items=[bundle_response(item) for item in items]
        )

    async def get_instrument(
        self,
        context: OrganizationContext,
        instrument_id: UUID,
    ) -> PaymentInstrument:
        item = await self.session.scalar(
            select(PaymentInstrument)
            .where(
                PaymentInstrument.id == instrument_id,
                PaymentInstrument.organization_id == context.organization_id,
            )
            .options(
                selectinload(PaymentInstrument.limits),
                selectinload(PaymentInstrument.payment_request),
            )
        )
        if item is None:
            raise PaymentInstrumentNotFound
        return item

    async def update_limits(
        self,
        context: OrganizationContext,
        user: User,
        instrument_id: UUID,
        body: PaymentLimitsRequest,
    ) -> PaymentInstrumentBundleResponse:
        item = await self.get_instrument(context, instrument_id)
        if item.status not in {"active", "frozen"}:
            raise InvalidPaymentTransition
        limits = provider_limits(body)
        previous = limits_response(item.limits).model_dump(mode="json")
        action = PaymentAction(
            organization_id=context.organization_id,
            instrument_id=item.id,
            requested_by_user_id=user.id,
            action="update_limits",
            status="pending",
            details_json=json.dumps(
                {
                    "before": previous,
                    "after": body.model_dump(mode="json"),
                },
                ensure_ascii=False,
            )
        )
        self.session.add(action)
        await self.session.commit()
        try:
            await self.provider.update_limits(item.external_id, limits)
        except Exception:
            action.status = "failed"
            await self.session.commit()
            raise
        item.limits.single_amount = limits.single
        item.limits.daily_amount = limits.daily
        item.limits.monthly_amount = limits.monthly
        item.limits.total_amount = limits.total
        action.status = "confirmed"
        await self.session.commit()
        return bundle_response(item)

    async def freeze(
        self,
        context: OrganizationContext,
        user: User,
        instrument_id: UUID,
    ) -> PaymentInstrumentBundleResponse:
        return await self._lifecycle_action(
            context,
            user,
            instrument_id,
            action="freeze",
            allowed={"active"},
            pending_status="freeze_pending",
        )

    async def unfreeze(
        self,
        context: OrganizationContext,
        user: User,
        instrument_id: UUID,
    ) -> PaymentInstrumentBundleResponse:
        return await self._lifecycle_action(
            context,
            user,
            instrument_id,
            action="unfreeze",
            allowed={"frozen"},
            pending_status="unfreeze_pending",
        )

    async def close(
        self,
        context: OrganizationContext,
        user: User,
        instrument_id: UUID,
    ) -> PaymentInstrumentBundleResponse:
        return await self._lifecycle_action(
            context,
            user,
            instrument_id,
            action="close",
            allowed={"active", "frozen"},
            pending_status="close_pending",
        )

    async def _lifecycle_action(
        self,
        context: OrganizationContext,
        user: User,
        instrument_id: UUID,
        *,
        action: str,
        allowed: set[str],
        pending_status: str,
    ) -> PaymentInstrumentBundleResponse:
        item = await self.get_instrument(context, instrument_id)
        if item.status not in allowed:
            raise InvalidPaymentTransition
        previous_status = item.status
        action_record = PaymentAction(
            organization_id=context.organization_id,
            instrument_id=item.id,
            requested_by_user_id=user.id,
            action=action,
            status="pending",
            details_json="{}",
        )
        item.status = pending_status
        self.session.add(action_record)
        await self.session.commit()

        provider_method = getattr(self.provider, action)
        try:
            provider_result = await provider_method(item.external_id)
        except Exception:
            item.status = previous_status
            action_record.status = "failed"
            await self.session.commit()
            raise
        item.status = (
            pending_status
            if provider_result.status == "pending"
            else provider_result.status
        )
        action_record.status = (
            "pending" if provider_result.status == "pending" else "confirmed"
        )
        await self.session.commit()
        return bundle_response(item)

    async def process_event(self, event: ProviderEvent) -> PaymentWebhookResponse:
        existing = await self.session.scalar(
            select(PaymentEvent).where(
                PaymentEvent.provider == self.provider_name,
                PaymentEvent.event_id == event.event_id,
            )
        )
        if existing is not None:
            return PaymentWebhookResponse(
                accepted=True,
                duplicate=True,
                event_id=event.event_id,
            )
        instrument = await self.session.scalar(
            select(PaymentInstrument).where(
                PaymentInstrument.provider == self.provider_name,
                PaymentInstrument.external_id == event.external_id,
            )
        )
        if instrument is None:
            raise PaymentInstrumentNotFound

        async with transaction(self.session):
            self.session.add(
                PaymentEvent(
                    organization_id=instrument.organization_id,
                    provider=self.provider_name,
                    event_id=event.event_id,
                    event_type=event.event_type,
                    instrument_id=instrument.id,
                    payload_json=json.dumps(event.payload, ensure_ascii=False),
                )
            )
            if event.event_type == "instrument.frozen":
                instrument.status = "frozen"
            elif event.event_type == "instrument.active":
                instrument.status = "active"
            elif event.event_type == "instrument.closed":
                instrument.status = "closed"
            elif event.event_type == "payment.settled":
                await self._record_settlement(instrument, event)
            await self.session.flush()
        return PaymentWebhookResponse(
            accepted=True,
            duplicate=False,
            event_id=event.event_id,
        )

    async def _record_settlement(
        self,
        instrument: PaymentInstrument,
        event: ProviderEvent,
    ) -> None:
        transaction_id = str(event.payload["transaction_id"])
        existing = await self.session.scalar(
            select(SpendTransaction).where(
                SpendTransaction.organization_id == instrument.organization_id,
                SpendTransaction.source_provider == self.provider_name,
                SpendTransaction.source_account_id == instrument.external_id,
                SpendTransaction.external_id == transaction_id,
            )
        )
        if existing is not None:
            return
        self.session.add(
            SpendTransaction(
                organization_id=instrument.organization_id,
                source_provider=self.provider_name,
                source_account_id=instrument.external_id,
                external_id=transaction_id,
                transaction_date=date.fromisoformat(
                    str(event.payload["transaction_date"])
                ),
                merchant_name=str(event.payload["merchant_name"]),
                description=str(event.payload["description"]),
                amount=quantize_money(Decimal(str(event.payload["amount"]))),
                currency=str(event.payload["currency"]),
                department=instrument.department,
                category="software",
                application_id=None,
                match_confidence=Decimal("1.0000"),
            )
        )
