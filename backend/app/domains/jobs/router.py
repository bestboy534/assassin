from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.infrastructure.queue.client import JobQueue, build_queue

from .models import Job, JobStatus
from .schemas import JobActionResponse, JobResponse
from .service import InvalidJobTransition, JobNotFoundError, JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def organization_id(
    x_organization_id: Annotated[UUID, Header(alias="X-Organization-ID")],
) -> UUID:
    return x_organization_id


def queue_from_request(request: Request) -> JobQueue:
    queue = getattr(request.app.state, "queue", None)
    return cast(JobQueue, queue) if queue is not None else build_queue()


def response_for(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        organization_id=job.organization_id,
        job_type=job.job_type,
        status=cast(JobStatus, job.status),
        progress=job.progress,
        result=job.result_json,
        error_code=job.error_code,
        error_detail=job.error_detail,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        retryable=job.retryable,
        trace_id=job.trace_id,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    org_id: Annotated[UUID, Depends(organization_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[JobQueue, Depends(queue_from_request)],
) -> JobResponse:
    try:
        return response_for(await JobService(session, queue).get(job_id, org_id))
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc


@router.post("/{job_id}/retry", response_model=JobActionResponse)
async def retry_job(
    job_id: UUID,
    org_id: Annotated[UUID, Depends(organization_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[JobQueue, Depends(queue_from_request)],
) -> JobActionResponse:
    try:
        job = await JobService(session, queue).retry(job_id, org_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except InvalidJobTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return JobActionResponse(id=job.id, status=cast(JobStatus, job.status))


@router.post("/{job_id}/cancel", response_model=JobActionResponse)
async def cancel_job(
    job_id: UUID,
    org_id: Annotated[UUID, Depends(organization_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[JobQueue, Depends(queue_from_request)],
) -> JobActionResponse:
    try:
        job = await JobService(session, queue).cancel(job_id, org_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except InvalidJobTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return JobActionResponse(id=job.id, status=cast(JobStatus, job.status))
