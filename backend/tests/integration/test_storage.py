from pathlib import Path
from uuid import uuid4

import pytest

from app.config import Settings
from app.core.database import Database
from app.domains.files.service import FileNotAvailable, FileService
from app.infrastructure.queue.client import InMemoryJobQueue
from app.infrastructure.storage.local import LocalObjectStorage


@pytest.mark.asyncio
async def test_uploaded_file_is_not_downloadable_before_scan(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        local_storage_path=tmp_path / "objects",
        enable_database=True,
    )
    storage = LocalObjectStorage(tmp_path / "objects", "test-secret")
    queue = InMemoryJobQueue()
    organization_id = uuid4()
    async with database.session_factory() as session:
        service = FileService(session, storage, queue, settings)
        stored_file, _ = await service.create_upload(
            organization_id,
            "invoice.pdf",
            "application/pdf",
        )
        storage.write_bytes(
            stored_file.quarantine_key,
            b"%PDF-1.7\nsample",
            "application/pdf",
        )

        with pytest.raises(FileNotAvailable):
            await service.create_download_url(stored_file.id, organization_id)

        processed = await service.process_scan(stored_file.id, organization_id)
        assert processed.status == "available"
        assert "local-download" in await service.create_download_url(
            stored_file.id,
            organization_id,
        )


@pytest.mark.asyncio
async def test_file_signature_mismatch_is_rejected(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        local_storage_path=tmp_path / "objects",
    )
    storage = LocalObjectStorage(tmp_path / "objects", "test-secret")
    queue = InMemoryJobQueue()
    organization_id = uuid4()
    async with database.session_factory() as session:
        service = FileService(session, storage, queue, settings)
        stored_file, _ = await service.create_upload(
            organization_id,
            "fake.pdf",
            "application/pdf",
        )
        storage.write_bytes(stored_file.quarantine_key, b"not a pdf", "application/pdf")

        processed = await service.process_scan(stored_file.id, organization_id)
        assert processed.status == "rejected"
        assert processed.rejection_reason == "file_signature_mismatch"


@pytest.mark.asyncio
async def test_known_malware_marker_is_rejected(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        local_storage_path=tmp_path / "objects",
    )
    storage = LocalObjectStorage(tmp_path / "objects", "test-secret")
    queue = InMemoryJobQueue()
    organization_id = uuid4()
    async with database.session_factory() as session:
        service = FileService(session, storage, queue, settings)
        stored_file, _ = await service.create_upload(
            organization_id,
            "unsafe.txt",
            "text/plain",
        )
        storage.write_bytes(
            stored_file.quarantine_key,
            b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE",
            "text/plain",
        )

        processed = await service.process_scan(stored_file.id, organization_id)
        assert processed.status == "rejected"
        assert processed.rejection_reason == "malware_detected"
