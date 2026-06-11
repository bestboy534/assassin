import asyncio
import logging
import signal
from uuid import UUID

from app.config import get_settings
from app.core.database import get_database
from app.domains.jobs.service import InvalidJobTransition, JobService
from app.infrastructure.storage.factory import build_storage

from .client import build_queue
from .jobs import TASK_HANDLERS

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    database = get_database()
    queue = build_queue(settings)
    storage = build_storage(settings)
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stopping.set)
        except NotImplementedError:
            signal.signal(
                signal_name,
                lambda _signum, _frame: loop.call_soon_threadsafe(stopping.set),
            )

    logger.info("Worker started queue=%s", settings.redis_queue_name)
    try:
        while not stopping.is_set():
            message = await queue.dequeue(settings.worker_poll_timeout_seconds)
            if message is None:
                continue
            handler = TASK_HANDLERS.get(message.task_name)
            async with database.session_factory() as session:
                jobs = JobService(session, queue)
                job_id = UUID(message.job_id)
                if handler is None:
                    await jobs.start(job_id)
                    await jobs.fail(
                        job_id,
                        code="unknown_task",
                        detail=message.task_name,
                        retryable=False,
                    )
                    continue
                try:
                    await jobs.start(job_id)
                    result = await handler(
                        session,
                        queue,
                        storage,
                        settings,
                        message.payload,
                    )
                    await jobs.succeed(job_id, result)
                except InvalidJobTransition:
                    logger.warning("Skipping terminal job job_id=%s", job_id)
                except Exception as exc:
                    logger.exception("Task failed job_id=%s task=%s", job_id, message.task_name)
                    await session.rollback()
                    try:
                        await jobs.fail(
                            job_id,
                            code="task_failed",
                            detail=str(exc),
                            retryable=True,
                        )
                    except InvalidJobTransition:
                        logger.warning("Could not mark job failed job_id=%s", job_id)
    finally:
        await queue.close()
        await database.dispose()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
