from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TgUser

from app.config import get_settings


def _get_telegram_user(event: TelegramObject) -> TgUser | None:
    if isinstance(event, Message):
        return event.from_user
    if isinstance(event, CallbackQuery):
        return event.from_user
    return None


class AdminFilter(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = _get_telegram_user(event)
        if not user:
            return False
        return user.id in get_settings().admin_id_list
