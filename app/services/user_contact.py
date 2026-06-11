from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.database.models import User


def format_user_display(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    if user.full_name:
        return user.full_name
    return "Пользователь"


def get_contact_url(user: User) -> str:
    if user.username:
        return f"https://t.me/{user.username}"
    return f"tg://user?id={user.telegram_id}"


def format_contact_line(user: User) -> str:
    return format_user_display(user)


def build_contact_keyboard(user: User, button_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=get_contact_url(user))]
        ]
    )


def build_dual_contact_keyboard(
    first_user: User,
    first_button_text: str,
    second_user: User,
    second_button_text: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=first_button_text, url=get_contact_url(first_user))],
            [InlineKeyboardButton(text=second_button_text, url=get_contact_url(second_user))],
        ]
    )
