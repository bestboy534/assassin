import asyncio
import logging
import signal

from app.config import get_settings
from app.core.database import get_database
from app.core.logging import configure_secure_logging
from app.infrastructure.secrets import LocalSecretCipher

from .delivery import HttpxWebhookSender, WebhookDeliveryService

logger = logging.getLogger(__name__)


async def run_webhook_worker() -> None:
    settings = get_settings()
    configure_secure_logging(settings.log_level)
    database = get_database()
    cipher = LocalSecretCipher(settings.webhook_secret_key.get_secret_value())
    sender = HttpxWebhookSender()
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

    logger.info("Webhook delivery worker started")
    try:
        while not stopping.is_set():
            async with database.session_factory() as session:
                deliveries = await WebhookDeliveryService(
                    session,
                    cipher,
                    sender,
                ).deliver_due(
                    limit=settings.webhook_delivery_batch_size,
                    max_attempts=settings.webhook_delivery_max_attempts,
                )
            if deliveries:
                logger.info("Processed webhook deliveries count=%s", len(deliveries))
                continue
            try:
                await asyncio.wait_for(
                    stopping.wait(),
                    timeout=settings.webhook_worker_poll_seconds,
                )
            except TimeoutError:
                pass
    finally:
        await database.dispose()


def main() -> None:
    asyncio.run(run_webhook_worker())


if __name__ == "__main__":
    main()
