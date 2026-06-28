import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from redis.exceptions import ReadOnlyError

from app.bot.handlers import setup_routers
from app.bot.middlewares.analytics import AnalyticsMiddleware
from app.bot.middlewares.db import DbSessionMiddleware
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

REDIS_WRITE_PROBE_KEY = "mentorly:redis_write_probe"


async def ensure_redis_writable(redis: Redis) -> None:
    try:
        await redis.set(REDIS_WRITE_PROBE_KEY, "1", ex=30)
        await redis.delete(REDIS_WRITE_PROBE_KEY)
    except ReadOnlyError as exc:
        logger.error(
            "Redis is read-only. FSM storage requires a writable primary Redis instance. "
            "Check REDIS_URL / REDIS_HOST in .env — do not use a read replica endpoint."
        )
        raise SystemExit(1) from exc


async def main() -> None:
    settings = get_settings()

    redis = Redis.from_url(settings.redis_url)
    await ensure_redis_writable(redis)
    storage = RedisStorage(redis=redis)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(AnalyticsMiddleware())
    dp.include_router(setup_routers())

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await redis.aclose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
