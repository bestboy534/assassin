import json
import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.transactions import transaction
from app.domains.identity.models import User
from app.domains.organizations.service import OrganizationContext
from app.llm_extractor import extract_subscriptions
from app.schemas import SourceType, SubscriptionItem
from app.service import to_subscription_item

from .models import AnalysisItem, AnalysisRun
from .schemas import (
    AnalysisRunDetailResponse,
    AnalysisRunListResponse,
    AnalysisRunResponse,
    CreateAnalysisRunRequest,
)


class AnalysisRunNotFound(Exception):
    pass


def analysis_run_response(run: AnalysisRun) -> AnalysisRunResponse:
    return AnalysisRunResponse(
        id=run.id,
        organization_id=run.organization_id,
        status=run.status,
        source_hint=cast(SourceType, run.source_hint),
        items_count=run.items_count,
        total_monthly_cost_usd=run.total_monthly_cost_usd,
        created_at=run.created_at,
    )


def analysis_item_response(item: AnalysisItem) -> SubscriptionItem:
    return SubscriptionItem(
        id=item.item_id,
        software_name=item.software_name,
        merchant_name=item.merchant_name,
        amount=item.amount,
        currency=item.currency,
        billing_cycle=item.billing_cycle,
        transaction_date=item.transaction_date,
        normalized_amount_usd=item.normalized_amount_usd,
        monthly_cost_usd=item.monthly_cost_usd,
        status=item.status,
        risk_type=item.risk_type,
        confidence=item.confidence,
        evidence=item.evidence,
        needs_user_confirmation=item.needs_user_confirmation,
        cancel_url=item.cancel_url,
        fallback_search_url=item.fallback_search_url,
        support_email=item.support_email,
        guide_steps=json.loads(item.guide_steps_json or "[]"),
        risk_note=item.risk_note,
    )


class BillingAuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_from_text(
        self,
        context: OrganizationContext,
        user: User,
        body: CreateAnalysisRunRequest,
    ) -> AnalysisRunDetailResponse:
        extracted = extract_subscriptions(body.raw_text, body.source_hint)
        subscription_items = [to_subscription_item(item) for item in extracted.items]
        run = AnalysisRun(
            id=f"run_{uuid.uuid4().hex[:12]}",
            organization_id=context.organization_id,
            created_by_user_id=user.id,
            source_hint=body.source_hint,
            items_count=len(subscription_items),
            status="completed",
            total_monthly_cost_usd=sum(item.monthly_cost_usd for item in subscription_items),
        )
        for position, item in enumerate(subscription_items):
            run.items.append(
                AnalysisItem(
                    item_id=item.id,
                    position=position,
                    software_name=item.software_name,
                    merchant_name=item.merchant_name,
                    amount=item.amount,
                    currency=item.currency,
                    billing_cycle=item.billing_cycle,
                    transaction_date=item.transaction_date,
                    normalized_amount_usd=item.normalized_amount_usd,
                    monthly_cost_usd=item.monthly_cost_usd,
                    status=item.status,
                    risk_type=item.risk_type,
                    confidence=item.confidence,
                    evidence=item.evidence,
                    needs_user_confirmation=item.needs_user_confirmation,
                    cancel_url=item.cancel_url,
                    fallback_search_url=item.fallback_search_url,
                    support_email=item.support_email,
                    guide_steps_json=json.dumps(item.guide_steps, ensure_ascii=False),
                    risk_note=item.risk_note,
                )
            )
        async with transaction(self.session):
            self.session.add(run)
        return AnalysisRunDetailResponse(
            run=analysis_run_response(run),
            items=[analysis_item_response(item) for item in run.items],
        )

    async def list(self, context: OrganizationContext) -> AnalysisRunListResponse:
        runs = (
            await self.session.scalars(
                select(AnalysisRun)
                .where(AnalysisRun.organization_id == context.organization_id)
                .order_by(AnalysisRun.created_at.desc())
            )
        ).all()
        return AnalysisRunListResponse(items=[analysis_run_response(run) for run in runs])

    async def get(
        self,
        context: OrganizationContext,
        run_id: str,
    ) -> AnalysisRunDetailResponse:
        run = await self.session.scalar(
            select(AnalysisRun)
            .where(
                AnalysisRun.id == run_id,
                AnalysisRun.organization_id == context.organization_id,
            )
            .options(selectinload(AnalysisRun.items))
        )
        if run is None:
            raise AnalysisRunNotFound
        return AnalysisRunDetailResponse(
            run=analysis_run_response(run),
            items=[analysis_item_response(item) for item in run.items],
        )
