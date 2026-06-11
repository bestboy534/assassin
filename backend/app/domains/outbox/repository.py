from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import InboxReceipt, OutboxEvent


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        event_type: str,
        aggregate_id: str | UUID,
        payload: dict[str, Any],
        *,
        organization_id: UUID | None = None,
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_type=event_type,
            aggregate_id=str(aggregate_id),
            organization_id=organization_id,
            payload=payload,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def claim_pending(
        self,
        *,
        limit: int = 100,
        stale_after: timedelta = timedelta(minutes=5),
    ) -> list[OutboxEvent]:
        now = datetime.now(UTC)
        stale_before = now - stale_after
        statement = (
            select(OutboxEvent)
            .where(
                OutboxEvent.available_at <= now,
                (
                    (OutboxEvent.status == "pending")
                    | (
                        (OutboxEvent.status == "processing")
                        & (OutboxEvent.locked_at < stale_before)
                    )
                ),
            )
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        events = list((await self.session.scalars(statement)).all())
        for event in events:
            event.status = "processing"
            event.locked_at = now
            event.attempts += 1
        await self.session.flush()
        return events

    async def mark_processed(self, event_id: UUID) -> None:
        await self.session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status="processed",
                processed_at=datetime.now(UTC),
                locked_at=None,
                last_error=None,
            )
        )

    async def mark_failed(
        self,
        event_id: UUID,
        error: str,
        *,
        max_attempts: int = 10,
    ) -> None:
        event = await self.session.get(OutboxEvent, event_id)
        if event is None:
            return
        event.status = "dead_letter" if event.attempts >= max_attempts else "pending"
        event.locked_at = None
        event.last_error = error[:500]
        if event.status == "pending":
            delay_seconds = min(2**event.attempts, 300)
            event.available_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)


async def record_inbox_receipt(
    session: AsyncSession,
    consumer: str,
    event_id: UUID,
) -> bool:
    receipt = InboxReceipt(consumer=consumer, event_id=event_id)
    nested = await session.begin_nested()
    try:
        session.add(receipt)
        await session.flush()
    except IntegrityError:
        await nested.rollback()
        return False
    await nested.commit()
    return True
