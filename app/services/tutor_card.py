import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TutorProfile
from app.database.repositories.tutors import MODERATION_HIDDEN, MODERATION_REJECTED

logger = logging.getLogger(__name__)

TELEGRAM_CAPTION_MAX = 1024
TELEGRAM_MESSAGE_MAX = 4096
TUTOR_DESCRIPTION_MAX = 2000


def truncate_text(text: str, limit: int, suffix: str = "…") -> str:
    if len(text) <= limit:
        return text
    if limit <= len(suffix):
        return suffix[:limit]
    return text[: limit - len(suffix)] + suffix


def format_tutor_header(tutor: TutorProfile) -> str:
    verified = "✅ Verified Mentor\n" if tutor.is_verified else ""
    return (
        f"{verified}👤 {tutor.name}, {tutor.age}\n"
        f"📍 {tutor.city}\n"
        f"🎓 {tutor.place_of_study}\n"
        f"💰 {tutor.price_min}–{tutor.price_max} ₸ / занятие"
    )


def format_moderation_status(tutor: TutorProfile) -> str | None:
    if tutor.moderation_status == MODERATION_HIDDEN:
        return "⛔ Анкета скрыта модератором"
    if tutor.moderation_status == MODERATION_REJECTED:
        return "⛔ Анкета отклонена модератором"
    return None


def format_tutor_description(tutor: TutorProfile) -> str:
    return f"📝 О себе:\n{tutor.description}"


def format_tutor_card(tutor: TutorProfile) -> str:
    return f"{format_tutor_header(tutor)}\n\n{format_tutor_description(tutor)}"


async def _send_text_parts(message: Message, text: str, limit: int = TELEGRAM_MESSAGE_MAX) -> None:
    remaining = text
    while remaining:
        chunk = remaining[:limit]
        await message.answer(chunk)
        remaining = remaining[limit:]


async def _send_text_card(
    message: Message,
    full_text: str,
    description: str,
    reply_markup: InlineKeyboardMarkup | None,
) -> None:
    text = truncate_text(full_text, TELEGRAM_MESSAGE_MAX)
    await message.answer(text, reply_markup=reply_markup)
    if len(full_text) > len(text):
        await _send_text_parts(message, description)


async def _clear_invalid_avatar(session: AsyncSession, tutor: TutorProfile) -> None:
    tutor.avatar_file_id = None
    await session.commit()
    logger.info("Cleared invalid avatar_file_id for tutor_id=%s", tutor.id)


async def _send_photo_card_to_chat(
    bot: Bot,
    chat_id: int,
    tutor: TutorProfile,
    full_text: str,
    header: str,
    description: str,
    reply_markup: InlineKeyboardMarkup | None,
    session: AsyncSession | None,
) -> bool:
    if not tutor.avatar_file_id:
        return False

    try:
        if len(full_text) <= TELEGRAM_CAPTION_MAX:
            await bot.send_photo(
                chat_id=chat_id,
                photo=tutor.avatar_file_id,
                caption=full_text,
                reply_markup=reply_markup,
            )
            return True

        caption_room = TELEGRAM_CAPTION_MAX - len(header) - 2
        if caption_room > 20:
            short_caption = f"{header}\n\n{truncate_text(description, caption_room)}"
        else:
            short_caption = truncate_text(header, TELEGRAM_CAPTION_MAX)

        await bot.send_photo(
            chat_id=chat_id,
            photo=tutor.avatar_file_id,
            caption=short_caption,
            reply_markup=reply_markup,
        )
        if len(full_text) > len(short_caption):
            remaining = description
            while remaining:
                chunk = remaining[:TELEGRAM_MESSAGE_MAX]
                await bot.send_message(chat_id=chat_id, text=chunk)
                remaining = remaining[TELEGRAM_MESSAGE_MAX:]
        return True
    except TelegramBadRequest as exc:
        logger.warning(
            "Avatar unavailable for tutor_id=%s file_id=%s: %s",
            tutor.id,
            tutor.avatar_file_id,
            exc,
        )
        if session is not None:
            await _clear_invalid_avatar(session, tutor)
        return False


async def send_tutor_card_to_chat(
    bot: Bot,
    chat_id: int,
    tutor: TutorProfile,
    reply_markup: InlineKeyboardMarkup | None = None,
    session: AsyncSession | None = None,
) -> None:
    header = format_tutor_header(tutor)
    description = format_tutor_description(tutor)
    full_text = f"{header}\n\n{description}"

    if tutor.avatar_file_id:
        sent = await _send_photo_card_to_chat(
            bot,
            chat_id,
            tutor,
            full_text,
            header,
            description,
            reply_markup,
            session,
        )
        if sent:
            return

    text = truncate_text(full_text, TELEGRAM_MESSAGE_MAX)
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    if len(full_text) > len(text):
        remaining = description
        while remaining:
            chunk = remaining[:TELEGRAM_MESSAGE_MAX]
            await bot.send_message(chat_id=chat_id, text=chunk)
            remaining = remaining[TELEGRAM_MESSAGE_MAX:]


async def _send_photo_card(
    message: Message,
    tutor: TutorProfile,
    full_text: str,
    header: str,
    description: str,
    reply_markup: InlineKeyboardMarkup | None,
    session: AsyncSession | None,
) -> bool:
    if not tutor.avatar_file_id:
        return False

    try:
        if len(full_text) <= TELEGRAM_CAPTION_MAX:
            await message.answer_photo(
                photo=tutor.avatar_file_id,
                caption=full_text,
                reply_markup=reply_markup,
            )
            return True

        caption_room = TELEGRAM_CAPTION_MAX - len(header) - 2
        if caption_room > 20:
            short_caption = f"{header}\n\n{truncate_text(description, caption_room)}"
        else:
            short_caption = truncate_text(header, TELEGRAM_CAPTION_MAX)

        await message.answer_photo(
            photo=tutor.avatar_file_id,
            caption=short_caption,
            reply_markup=reply_markup,
        )
        if len(full_text) > len(short_caption):
            await _send_text_parts(message, description)
        return True
    except TelegramBadRequest as exc:
        logger.warning(
            "Avatar unavailable for tutor_id=%s file_id=%s: %s",
            tutor.id,
            tutor.avatar_file_id,
            exc,
        )
        if session is not None:
            await _clear_invalid_avatar(session, tutor)
        return False


async def send_tutor_card(
    message: Message,
    tutor: TutorProfile,
    reply_markup: InlineKeyboardMarkup | None = None,
    session: AsyncSession | None = None,
) -> None:
    header = format_tutor_header(tutor)
    description = format_tutor_description(tutor)
    full_text = f"{header}\n\n{description}"

    if tutor.avatar_file_id:
        sent = await _send_photo_card(
            message,
            tutor,
            full_text,
            header,
            description,
            reply_markup,
            session,
        )
        if sent:
            return

    await _send_text_card(message, full_text, description, reply_markup)
