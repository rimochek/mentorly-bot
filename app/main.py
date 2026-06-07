import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.bot.handlers import setup_routers
from app.bot.middlewares.db import DbSessionMiddleware
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()

    redis = Redis.from_url(settings.redis_url)
    storage = RedisStorage(redis=redis)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(setup_routers())

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await redis.aclose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
