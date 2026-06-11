import json
from dataclasses import asdict, dataclass
from typing import Any, Protocol
from uuid import UUID

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class QueueMessage:
    job_id: str
    task_name: str
    payload: dict[str, Any]


class JobQueue(Protocol):
    async def enqueue(
        self,
        job_id: UUID,
        task_name: str,
        payload: dict[str, Any],
    ) -> None: ...

    async def dequeue(self, timeout: int = 5) -> QueueMessage | None: ...

    async def ping(self) -> bool: ...

    async def close(self) -> None: ...


class InMemoryJobQueue:
    def __init__(self) -> None:
        self.messages: list[QueueMessage] = []

    async def enqueue(
        self,
        job_id: UUID,
        task_name: str,
        payload: dict[str, Any],
    ) -> None:
        self.messages.append(QueueMessage(str(job_id), task_name, payload))

    async def dequeue(self, timeout: int = 5) -> QueueMessage | None:
        del timeout
        return self.messages.pop(0) if self.messages else None

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class RedisJobQueue:
    def __init__(self, redis_url: str, queue_name: str) -> None:
        from redis.asyncio import Redis

        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.queue_name = queue_name

    async def enqueue(
        self,
        job_id: UUID,
        task_name: str,
        payload: dict[str, Any],
    ) -> None:
        message = QueueMessage(str(job_id), task_name, payload)
        await self.redis.rpush(self.queue_name, json.dumps(asdict(message)))

    async def dequeue(self, timeout: int = 5) -> QueueMessage | None:
        result = await self.redis.blpop(self.queue_name, timeout=timeout)
        if result is None:
            return None
        _, value = result
        raw = json.loads(value)
        return QueueMessage(
            job_id=raw["job_id"],
            task_name=raw["task_name"],
            payload=raw["payload"],
        )

    async def ping(self) -> bool:
        try:
            return bool(await self.redis.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self.redis.aclose()


def build_queue(settings: Settings | None = None) -> JobQueue:
    resolved = settings or get_settings()
    if resolved.queue_backend == "redis":
        return RedisJobQueue(resolved.redis_url, resolved.redis_queue_name)
    return InMemoryJobQueue()
