from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.bot.keyboards.reply import (
    BROWSE_BUTTONS,
    BUDGET_BUTTONS,
    EXAM_BUTTONS,
    LEVEL_BUTTONS,
    MAIN_MENU_BUTTONS,
    SHARE_LOCATION,
    SKIP_PHOTO,
    TUTOR_CABINET_BUTTONS,
)
from app.services.analytics import EVENT_BUTTON, EVENT_CALLBACK, track_event

KNOWN_BUTTONS = frozenset(
    MAIN_MENU_BUTTONS
    + BROWSE_BUTTONS
    + TUTOR_CABINET_BUTTONS
    + EXAM_BUTTONS
    + LEVEL_BUTTONS
    + BUDGET_BUTTONS
    + [SKIP_PHOTO, SHARE_LOCATION, "🧑‍🏫 Стать репетитором"]
)


def _is_trackable_callback(data: str) -> bool:
    if data in {"next_tutor", "main_menu", "edit:back"}:
        return True
    return data.startswith("contact:") or data.startswith("edit:")


class AnalyticsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        result = await handler(event, data)

        if not isinstance(event, Update):
            return result

        message = event.message
        if message and message.from_user and message.text in KNOWN_BUTTONS:
            await track_event(message.from_user.id, EVENT_BUTTON, message.text)
            return result

        callback = event.callback_query
        if (
            callback
            and callback.from_user
            and callback.data
            and _is_trackable_callback(callback.data)
        ):
            await track_event(callback.from_user.id, EVENT_CALLBACK, callback.data)

        return result
