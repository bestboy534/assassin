from uuid import UUID

from pydantic import BaseModel, Field


class CreateUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=150)


class UploadResponse(BaseModel):
    id: UUID
    status: str
    upload_url: str
    expires_in: int


class CompleteUploadResponse(BaseModel):
    id: UUID
    status: str
    job_id: UUID


class DownloadResponse(BaseModel):
    id: UUID
    download_url: str
    expires_in: int


class FileResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int | None
    status: str
    rejection_reason: str | None
