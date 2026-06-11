"""Compatibility repository for the existing bill-audit endpoints."""

import json
import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .domains.audit_ai.models import AnalysisItem, AnalysisRun
from .schemas import HistoryRun, SourceType, SubscriptionItem


async def save_analysis_run(
    session: AsyncSession,
    source_hint: SourceType,
    items: list[SubscriptionItem],
) -> str:
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    run = AnalysisRun(id=run_id, source_hint=source_hint, items_count=len(items))
    for position, item in enumerate(items):
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
    session.add(run)
    await session.commit()
    return run_id


async def list_history_runs(session: AsyncSession, limit: int = 20) -> list[HistoryRun]:
    statement = select(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(limit)
    runs = (await session.scalars(statement)).all()
    return [
        HistoryRun(
            id=run.id,
            created_at=run.created_at.isoformat(),
            source_hint=cast(SourceType, run.source_hint),
            items_count=run.items_count,
        )
        for run in runs
    ]


async def get_history_run(
    session: AsyncSession,
    run_id: str,
) -> tuple[HistoryRun, list[SubscriptionItem]] | None:
    statement = (
        select(AnalysisRun).where(AnalysisRun.id == run_id).options(selectinload(AnalysisRun.items))
    )
    run = await session.scalar(statement)
    if run is None:
        return None

    history_run = HistoryRun(
        id=run.id,
        created_at=run.created_at.isoformat(),
        source_hint=cast(SourceType, run.source_hint),
        items_count=run.items_count,
    )
    items = [
        SubscriptionItem(
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
        for item in run.items
    ]
    return history_run, items
