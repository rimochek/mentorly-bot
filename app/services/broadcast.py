import logging

from aiogram import Bot

logger = logging.getLogger(__name__)

AUDIENCE_LABELS = {
    "all": "всем пользователям",
    "tutors": "репетиторам",
    "students": "ученикам",
}


async def send_broadcast(bot: Bot, telegram_ids: list[int], text: str) -> tuple[int, int]:
    sent = 0
    failed = 0
    for telegram_id in telegram_ids:
        try:
            await bot.send_message(telegram_id, text)
            sent += 1
        except Exception:
            logger.exception("Broadcast failed for telegram_id=%s", telegram_id)
            failed += 1
    return sent, failed
