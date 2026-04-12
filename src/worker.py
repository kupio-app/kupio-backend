import asyncio
import logging

from uuid import UUID
from firebase_admin import messaging
from streaq import Worker, WorkerDepends

from src.core.config import get_config
from src.core.worker.context import WorkerContext, lifespan
from src.core.database.repositories import Repositories
from src.domains.promotions.repository import ListingPromotionsRepository

logger = logging.getLogger(__name__)

config = get_config()

worker = Worker(
    redis_url=config.redis.build_url(),
    lifespan=lifespan,
)


@worker.cron("*/5 * * * *")
async def deactivate_expired_promotions(ctx: WorkerContext = WorkerDepends()) -> None:
    async with ctx.session_factory() as session:
        repo = ListingPromotionsRepository(session=session)
        count = await repo.bulk_expire()
        await session.commit()

    logger.info("Deactivated %d expired promotions", count)


@worker.task()
async def send_fcm_push(
    recipient_user_id: str,
    conversation_id: str,
    message_preview: str,
    ctx: WorkerContext = WorkerDepends(),
) -> None:
    async with ctx.session_factory() as session:
        repos = Repositories.from_session(session)
        notification_tokens = await repos.notification_tokens.get_tokens_for_user(
            UUID(recipient_user_id)
        )
        if not notification_tokens:
            return

        loop = asyncio.get_running_loop()
        dead_token_ids: list[UUID] = []

        for notification_token in notification_tokens:
            fcm_message = messaging.Message(
                notification=messaging.Notification(
                    title="New message",
                    body=message_preview,
                ),
                data={
                    "conversation_id": conversation_id,
                    "type": "chat_message",
                },
                token=notification_token.token,
            )

            try:
                await loop.run_in_executor(
                    None, lambda m: messaging.send(m), fcm_message
                )
            except messaging.UnregisteredError:
                logger.info(
                    "FCM token unregistered, marking for deletion: %s",
                    notification_token.id,
                )
                dead_token_ids.append(notification_token.id)
            except Exception:
                logger.exception("FCM send failed for token %s", notification_token.id)

        if dead_token_ids:
            for tid in dead_token_ids:
                await repos.notification_tokens.delete_by_id(tid)

            await session.commit()
