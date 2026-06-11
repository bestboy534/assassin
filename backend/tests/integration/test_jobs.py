from uuid import uuid4

import pytest

from app.core.database import Database
from app.domains.jobs.service import (
    InvalidJobTransition,
    JobNotFoundError,
    JobService,
)
from app.infrastructure.queue.client import InMemoryJobQueue


@pytest.mark.asyncio
async def test_job_transitions_are_valid(database: Database) -> None:
    organization_id = uuid4()
    queue = InMemoryJobQueue()
    async with database.session_factory() as session:
        service = JobService(session, queue)
        job = await service.create("audit.parse", organization_id)
        await service.enqueue(job, {"analysis_run_id": "run_1"})
        await service.start(job.id)
        await service.succeed(job.id, result={"analysis_run_id": "run_1"})

        assert (await service.get(job.id)).status == "succeeded"
        with pytest.raises(InvalidJobTransition):
            await service.fail(job.id, code="late_failure")


@pytest.mark.asyncio
async def test_job_lookup_is_tenant_scoped(database: Database) -> None:
    queue = InMemoryJobQueue()
    async with database.session_factory() as session:
        service = JobService(session, queue)
        job = await service.create("audit.parse", uuid4())
        await session.commit()

        with pytest.raises(JobNotFoundError):
            await service.get(job.id, uuid4())
