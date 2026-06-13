from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import get_session
from app.domains.billing.service import EntitlementExceeded
from app.domains.jobs.router import organization_id, queue_from_request
from app.domains.jobs.service import JobService
from app.infrastructure.queue.client import InMemoryJobQueue, JobQueue
from app.infrastructure.storage.base import ObjectStorage
from app.infrastructure.storage.factory import build_storage
from app.infrastructure.storage.local import InvalidStorageSignature, LocalObjectStorage

from .models import StoredFile
from .schemas import (
    CompleteUploadResponse,
    CreateUploadRequest,
    DownloadResponse,
    FileResponse,
    UploadResponse,
)
from .service import FileNotAvailable, FileNotFoundError, FileService

router = APIRouter(prefix="/files", tags=["files"])


def storage_from_request(request: Request) -> ObjectStorage:
    storage = getattr(request.app.state, "storage", None)
    return cast(ObjectStorage, storage) if storage is not None else build_storage()


def file_response(file_model: StoredFile) -> FileResponse:
    return FileResponse(
        id=file_model.id,
        filename=file_model.filename,
        content_type=file_model.content_type,
        size_bytes=file_model.size_bytes,
        status=file_model.status,
        rejection_reason=file_model.rejection_reason,
    )


@router.post("/uploads", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(
    body: CreateUploadRequest,
    org_id: Annotated[UUID, Depends(organization_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[JobQueue, Depends(queue_from_request)],
    storage: Annotated[ObjectStorage, Depends(storage_from_request)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UploadResponse:
    stored_file, upload_url = await FileService(session, storage, queue, settings).create_upload(
        org_id, body.filename, body.content_type
    )
    return UploadResponse(
        id=stored_file.id,
        status=stored_file.status,
        upload_url=upload_url,
        expires_in=settings.storage_presign_expires_seconds,
    )


@router.post("/{file_id}/complete", response_model=CompleteUploadResponse)
async def complete_upload(
    file_id: UUID,
    org_id: Annotated[UUID, Depends(organization_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[JobQueue, Depends(queue_from_request)],
    storage: Annotated[ObjectStorage, Depends(storage_from_request)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CompleteUploadResponse:
    service = FileService(session, storage, queue, settings)
    try:
        stored_file, job = await service.complete_upload(file_id, org_id)
        if isinstance(queue, InMemoryJobQueue):
            await queue.dequeue(timeout=0)
            job_service = JobService(session, queue)
            await job_service.start(job.id)
            stored_file = await service.process_scan(file_id, org_id)
            if stored_file.status == "available":
                await job_service.succeed(
                    job.id,
                    {"file_id": str(file_id), "status": stored_file.status},
                )
            else:
                await job_service.fail(
                    job.id,
                    code=stored_file.rejection_reason or "scan_rejected",
                    retryable=False,
                )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    except FileNotAvailable as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except EntitlementExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "entitlement_exceeded",
                "entitlement": exc.entitlement,
                "current": exc.current,
                "limit": exc.limit,
                "increment": exc.increment,
                "plan": exc.plan,
            },
        ) from exc
    return CompleteUploadResponse(id=stored_file.id, status=stored_file.status, job_id=job.id)


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: UUID,
    org_id: Annotated[UUID, Depends(organization_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[JobQueue, Depends(queue_from_request)],
    storage: Annotated[ObjectStorage, Depends(storage_from_request)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    try:
        stored_file = await FileService(session, storage, queue, settings).get(file_id, org_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    return file_response(stored_file)


@router.get("/{file_id}/download", response_model=DownloadResponse)
async def download_file(
    file_id: UUID,
    org_id: Annotated[UUID, Depends(organization_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[JobQueue, Depends(queue_from_request)],
    storage: Annotated[ObjectStorage, Depends(storage_from_request)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DownloadResponse:
    try:
        download_url = await FileService(session, storage, queue, settings).create_download_url(
            file_id, org_id
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    except FileNotAvailable as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DownloadResponse(
        id=file_id,
        download_url=download_url,
        expires_in=settings.storage_presign_expires_seconds,
    )


@router.delete("/{file_id}", response_model=FileResponse)
async def delete_file(
    file_id: UUID,
    org_id: Annotated[UUID, Depends(organization_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[JobQueue, Depends(queue_from_request)],
    storage: Annotated[ObjectStorage, Depends(storage_from_request)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    try:
        stored_file = await FileService(session, storage, queue, settings).delete(file_id, org_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    return file_response(stored_file)


@router.put("/local-upload/{key:path}", include_in_schema=False)
async def local_upload(
    key: str,
    request: Request,
    expires: Annotated[int, Query()],
    signature: Annotated[str, Query()],
    storage: Annotated[ObjectStorage, Depends(storage_from_request)],
) -> Response:
    if not isinstance(storage, LocalObjectStorage):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        storage.verify("/api/v1/files/local-upload", key, expires, signature)
    except InvalidStorageSignature as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    content_type = request.headers.get("content-type", "application/octet-stream")
    storage.write_bytes(key, await request.body(), content_type)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/local-download/{key:path}", include_in_schema=False)
async def local_download(
    key: str,
    expires: Annotated[int, Query()],
    signature: Annotated[str, Query()],
    storage: Annotated[ObjectStorage, Depends(storage_from_request)],
) -> Response:
    if not isinstance(storage, LocalObjectStorage):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        storage.verify("/api/v1/files/local-download", key, expires, signature)
    except InvalidStorageSignature as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return Response(content=storage.read_bytes(key), media_type="application/octet-stream")
