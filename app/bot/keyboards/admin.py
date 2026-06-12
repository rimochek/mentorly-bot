from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.database.models import TutorProfile, User
from app.database.repositories.tutors import MODERATION_APPROVED, MODERATION_HIDDEN, MODERATION_REJECTED
from app.services.user_contact import build_contact_keyboard


def admin_profiles_filter_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Все", callback_data="adm:filter:all"),
                InlineKeyboardButton(text="Скрытые", callback_data="adm:filter:hidden"),
            ],
            [InlineKeyboardButton(text="Новые (7 дней)", callback_data="adm:filter:recent")],
        ]
    )


def admin_moderation_keyboard(tutor: TutorProfile, tutor_user: User | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if tutor.moderation_status == MODERATION_APPROVED:
        rows.append([
            InlineKeyboardButton(text="Скрыть", callback_data=f"adm:hide:{tutor.id}"),
            InlineKeyboardButton(text="Отклонить", callback_data=f"adm:reject:{tutor.id}"),
        ])
    else:
        rows.append([
            InlineKeyboardButton(text="Восстановить", callback_data=f"adm:restore:{tutor.id}"),
        ])

    verify_label = "Снять Verified" if tutor.is_verified else "Verified Mentor"
    rows.append([
        InlineKeyboardButton(text=verify_label, callback_data=f"adm:verify:{tutor.id}"),
        InlineKeyboardButton(text="Следующая", callback_data="adm:next"),
    ])

    if tutor_user:
        contact_kb = build_contact_keyboard(tutor_user, "Написать")
        rows.extend(contact_kb.inline_keyboard)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_moderation_status_label(tutor: TutorProfile) -> str:
    if tutor.moderation_status == MODERATION_HIDDEN:
        return "скрыта"
    if tutor.moderation_status == MODERATION_REJECTED:
        return "отклонена"
    return "одобрена"
