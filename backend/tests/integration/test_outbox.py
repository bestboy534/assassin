from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.database import Database
from app.core.transactions import transaction
from app.domains.audit_ai.models import AnalysisRun
from app.domains.outbox.models import InboxReceipt, OutboxEvent
from app.domains.outbox.repository import OutboxRepository, record_inbox_receipt


@pytest.mark.asyncio
async def test_business_write_and_outbox_commit_together(database: Database) -> None:
    async with database.session_factory() as session:
        outbox = OutboxRepository(session)
        async with transaction(session):
            run = AnalysisRun(id="run_outbox", source_hint="csv", items_count=0)
            session.add(run)
            await outbox.add("analysis.created", run.id, {"source_hint": run.source_hint})

    async with database.session_factory() as session:
        assert await session.get(AnalysisRun, "run_outbox") is not None
        assert await session.scalar(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == "run_outbox")
        )


@pytest.mark.asyncio
async def test_business_write_and_outbox_roll_back_together(database: Database) -> None:
    async with database.session_factory() as session:
        with pytest.raises(RuntimeError):
            async with transaction(session):
                session.add(AnalysisRun(id="run_failed_outbox", source_hint="csv", items_count=0))
                await OutboxRepository(session).add(
                    "analysis.created",
                    "run_failed_outbox",
                    {},
                )
                raise RuntimeError("rollback")

        assert await session.scalar(select(func.count(OutboxEvent.id))) == 0


@pytest.mark.asyncio
async def test_inbox_receipt_is_idempotent(database: Database) -> None:
    event_id = uuid4()
    async with database.session_factory() as session:
        async with transaction(session):
            assert await record_inbox_receipt(session, "reporting", event_id)
            assert not await record_inbox_receipt(session, "reporting", event_id)

    async with database.session_factory() as session:
        count = await session.scalar(select(func.count(InboxReceipt.id)))
        assert count == 1
