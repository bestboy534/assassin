import pytest
from sqlalchemy import func, select

from app.core.database import Database
from app.core.transactions import transaction
from app.domains.audit_ai.models import AnalysisRun


@pytest.mark.asyncio
async def test_transaction_rolls_back_all_changes(database: Database) -> None:
    async with database.session_factory() as session:
        with pytest.raises(RuntimeError, match="force rollback"):
            async with transaction(session):
                session.add(
                    AnalysisRun(
                        id="run_rollback",
                        source_hint="csv",
                        items_count=0,
                    )
                )
                raise RuntimeError("force rollback")

        count = await session.scalar(select(func.count(AnalysisRun.id)))
        assert count == 0


@pytest.mark.asyncio
async def test_transaction_commits_all_changes(database: Database) -> None:
    async with database.session_factory() as session:
        async with transaction(session):
            session.add(
                AnalysisRun(
                    id="run_commit",
                    source_hint="csv",
                    items_count=0,
                )
            )

    async with database.session_factory() as session:
        assert await session.get(AnalysisRun, "run_commit") is not None
