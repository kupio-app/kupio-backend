import logging

from streaq import Worker, WorkerDepends

from src.core.config import get_config
from src.core.worker.context import WorkerContext, lifespan
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
