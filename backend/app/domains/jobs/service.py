from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.queue.client import JobQueue

from .models import Job, JobStatus

VALID_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"running", "cancelled"},
    "running": {"succeeded", "failed", "cancelled"},
    "succeeded": set(),
    "failed": {"queued"},
    "cancelled": set(),
}


class JobNotFoundError(LookupError):
    pass


class InvalidJobTransition(ValueError):
    pass


class JobService:
    def __init__(self, session: AsyncSession, queue: JobQueue) -> None:
        self.session = session
        self.queue = queue

    async def create(
        self,
        job_type: str,
        organization_id: UUID,
        *,
        trace_id: str | None = None,
        max_attempts: int = 3,
    ) -> Job:
        job = Job(
            organization_id=organization_id,
            job_type=job_type,
            trace_id=trace_id,
            max_attempts=max_attempts,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get(self, job_id: UUID, organization_id: UUID | None = None) -> Job:
        statement = select(Job).where(Job.id == job_id)
        if organization_id is not None:
            statement = statement.where(Job.organization_id == organization_id)
        job = await self.session.scalar(statement)
        if job is None:
            raise JobNotFoundError(str(job_id))
        return job

    async def enqueue(
        self,
        job: Job,
        payload: dict[str, Any],
        *,
        commit: bool = True,
    ) -> None:
        job.payload_json = payload
        if commit:
            await self.session.commit()
        await self.queue.enqueue(job.id, job.job_type, payload)

    async def start(self, job_id: UUID) -> Job:
        job = await self.get(job_id)
        self._transition(job, "running")
        job.started_at = datetime.now(UTC)
        job.attempts += 1
        await self.session.commit()
        return job

    async def update_progress(self, job_id: UUID, progress: int) -> Job:
        job = await self.get(job_id)
        if job.status != "running":
            raise InvalidJobTransition(f"Cannot update progress for {job.status} job")
        job.progress = max(0, min(progress, 100))
        await self.session.commit()
        return job

    async def succeed(self, job_id: UUID, result: dict[str, Any] | None = None) -> Job:
        job = await self.get(job_id)
        self._transition(job, "succeeded")
        job.progress = 100
        job.result_json = result
        job.finished_at = datetime.now(UTC)
        await self.session.commit()
        return job

    async def fail(
        self,
        job_id: UUID,
        *,
        code: str,
        detail: str | None = None,
        retryable: bool = True,
    ) -> Job:
        job = await self.get(job_id)
        self._transition(job, "failed")
        job.error_code = code
        job.error_detail = detail
        job.retryable = retryable
        job.finished_at = datetime.now(UTC)
        await self.session.commit()
        return job

    async def cancel(self, job_id: UUID, organization_id: UUID) -> Job:
        job = await self.get(job_id, organization_id)
        self._transition(job, "cancelled")
        job.finished_at = datetime.now(UTC)
        await self.session.commit()
        return job

    async def retry(self, job_id: UUID, organization_id: UUID) -> Job:
        job = await self.get(job_id, organization_id)
        if not job.retryable or job.attempts >= job.max_attempts:
            raise InvalidJobTransition("Job is not retryable")
        self._transition(job, "queued")
        job.progress = 0
        job.error_code = None
        job.error_detail = None
        job.finished_at = None
        await self.session.commit()
        await self.queue.enqueue(job.id, job.job_type, job.payload_json)
        return job

    @staticmethod
    def _transition(job: Job, target: JobStatus) -> None:
        if target not in VALID_TRANSITIONS[job.status]:
            raise InvalidJobTransition(f"Cannot transition job from {job.status} to {target}")
        job.status = cast(str, target)
