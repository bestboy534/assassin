import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.domains.jobs.models import Job
from app.domains.jobs.service import JobService
from app.infrastructure.queue.client import JobQueue
from app.infrastructure.storage.base import ObjectStorage
from app.infrastructure.storage.scanner import FileScanner

from .models import StoredFile

SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class FileNotFoundError(LookupError):
    pass


class FileNotAvailable(ValueError):
    pass


class FileService:
    def __init__(
        self,
        session: AsyncSession,
        storage: ObjectStorage,
        queue: JobQueue,
        settings: Settings,
    ) -> None:
        self.session = session
        self.storage = storage
        self.queue = queue
        self.settings = settings

    async def create_upload(
        self,
        organization_id: UUID,
        filename: str,
        content_type: str,
    ) -> tuple[StoredFile, str]:
        safe_filename = SAFE_FILENAME.sub("_", filename).strip("._") or "upload"
        stored_file = StoredFile(
            organization_id=organization_id,
            filename=safe_filename,
            content_type=content_type,
            quarantine_key="pending",
        )
        self.session.add(stored_file)
        await self.session.flush()
        stored_file.quarantine_key = (
            f"quarantine/{organization_id}/{stored_file.id}/{safe_filename}"
        )
        await self.session.commit()
        upload_url = self.storage.presign_upload(
            stored_file.quarantine_key,
            content_type,
            self.settings.storage_presign_expires_seconds,
        )
        return stored_file, upload_url

    async def complete_upload(
        self,
        file_id: UUID,
        organization_id: UUID,
    ) -> tuple[StoredFile, Job]:
        stored_file = await self.get(file_id, organization_id)
        if stored_file.status != "quarantined":
            raise FileNotAvailable(f"Cannot complete file in {stored_file.status} state")
        try:
            info = self.storage.stat(stored_file.quarantine_key)
        except OSError as exc:
            raise FileNotAvailable("Uploaded object was not found") from exc
        stored_file.size_bytes = info.size
        stored_file.status = "uploaded"
        job_service = JobService(self.session, self.queue)
        job = await job_service.create("file.scan", organization_id)
        await job_service.enqueue(
            job,
            {
                "file_id": str(stored_file.id),
                "organization_id": str(organization_id),
            },
        )
        return stored_file, job

    async def process_scan(self, file_id: UUID, organization_id: UUID) -> StoredFile:
        stored_file = await self.get(file_id, organization_id)
        if stored_file.status not in {"quarantined", "uploaded", "scanning"}:
            return stored_file
        stored_file.status = "scanning"
        await self.session.flush()
        result = FileScanner(self.settings.max_upload_bytes).scan(
            self.storage,
            stored_file.quarantine_key,
            stored_file.content_type,
        )
        if not result.clean:
            stored_file.status = "rejected"
            stored_file.rejection_reason = result.reason
            self.storage.delete(stored_file.quarantine_key)
            await self.session.commit()
            return stored_file

        destination = f"files/{organization_id}/{stored_file.id}/{stored_file.filename}"
        self.storage.move(stored_file.quarantine_key, destination)
        stored_file.storage_key = destination
        stored_file.status = "available"
        stored_file.rejection_reason = None
        await self.session.commit()
        return stored_file

    async def create_download_url(
        self,
        file_id: UUID,
        organization_id: UUID,
    ) -> str:
        stored_file = await self.get(file_id, organization_id)
        if stored_file.status != "available" or stored_file.storage_key is None:
            raise FileNotAvailable("File is not available for download")
        return self.storage.presign_download(
            stored_file.storage_key,
            self.settings.storage_presign_expires_seconds,
        )

    async def delete(self, file_id: UUID, organization_id: UUID) -> StoredFile:
        stored_file = await self.get(file_id, organization_id)
        key = stored_file.storage_key or stored_file.quarantine_key
        self.storage.delete(key)
        stored_file.status = "deleted"
        await self.session.commit()
        return stored_file

    async def get(self, file_id: UUID, organization_id: UUID) -> StoredFile:
        statement = select(StoredFile).where(
            StoredFile.id == file_id,
            StoredFile.organization_id == organization_id,
        )
        stored_file = await self.session.scalar(statement)
        if stored_file is None:
            raise FileNotFoundError(str(file_id))
        return stored_file
