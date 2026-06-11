from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.domains.files.service import FileService
from app.infrastructure.queue.client import JobQueue
from app.infrastructure.storage.base import ObjectStorage

TaskHandler = Callable[
    [AsyncSession, JobQueue, ObjectStorage, Settings, dict[str, Any]],
    Awaitable[dict[str, Any] | None],
]


async def scan_file(
    session: AsyncSession,
    queue: JobQueue,
    storage: ObjectStorage,
    settings: Settings,
    payload: dict[str, Any],
) -> dict[str, Any]:
    file_id = UUID(str(payload["file_id"]))
    organization_id = UUID(str(payload["organization_id"]))
    stored_file = await FileService(
        session,
        storage,
        queue,
        settings,
    ).process_scan(file_id, organization_id)
    return {"file_id": str(stored_file.id), "status": stored_file.status}


TASK_HANDLERS: dict[str, TaskHandler] = {
    "file.scan": scan_file,
}
