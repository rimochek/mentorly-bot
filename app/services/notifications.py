import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from app.config import get_settings
from app.bot.keyboards.admin import admin_moderation_keyboard
from app.database.models import Application, StudentSearch, TutorProfile, User
from app.services.tutor_card import send_tutor_card_to_chat
from app.services.user_contact import (
    build_contact_keyboard,
    build_dual_contact_keyboard,
    format_user_display,
)

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.admin_ids = get_settings().admin_id_list

    async def _notify_admins(
        self,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(admin_id, text, reply_markup=reply_markup)
            except Exception:
                logger.exception("Failed to notify admin %s", admin_id)

    async def notify_new_tutor_profile(self, profile: TutorProfile, user: User) -> None:
        keyboard = admin_moderation_keyboard(profile, user)
        for admin_id in self.admin_ids:
            try:
                await send_tutor_card_to_chat(
                    self.bot,
                    admin_id,
                    profile,
                    reply_markup=keyboard,
                )
            except Exception:
                logger.exception("Failed to notify admin %s about new tutor profile", admin_id)

    async def notify_new_application(
        self,
        application: Application,
        student: User,
        tutor_profile: TutorProfile,
        tutor_user: User,
    ) -> None:
        admin_text = (
            "Новая заявка:\n\n"
            f"Ученик: {format_user_display(student)}\n"
            f"Репетитор: {tutor_profile.name} ({format_user_display(tutor_user)})\n\n"
            f"Экзамен: {application.exam_keyword}\n"
            f"Цель: {application.goal}\n"
            f"Уровень: {application.current_level}\n"
            f"Бюджет: {application.budget_text}"
        )
        admin_keyboard = build_dual_contact_keyboard(
            student,
            "Написать ученику",
            tutor_user,
            "Написать репетитору",
        )
        await self._notify_admins(admin_text, reply_markup=admin_keyboard)

        tutor_text = (
            "У тебя новая заявка 👀\n\n"
            f"Ученик: {format_user_display(student)}\n"
            f"Экзамен: {application.exam_keyword}\n"
            f"Цель: {application.goal}\n"
            f"Уровень: {application.current_level}\n"
            f"Бюджет: {application.budget_text}"
        )
        if not student.username:
            tutor_text += (
                "\n\nЕсли кнопка не открывает чат, напишите администратору."
            )

        tutor_keyboard = build_contact_keyboard(student, "Открыть чат с учеником")

        try:
            await self.bot.send_message(
                tutor_user.telegram_id,
                tutor_text,
                reply_markup=tutor_keyboard,
            )
        except Exception:
            logger.exception("Failed to notify tutor %s", tutor_user.telegram_id)

    async def notify_support_complaint(self, user: User, text: str) -> None:
        admin_text = (
            "🆘 Обращение в техподдержку:\n\n"
            f"Пользователь: {format_user_display(user)}\n\n"
            f"Сообщение:\n{text}"
        )
        keyboard = build_contact_keyboard(user, "Написать пользователю")
        await self._notify_admins(admin_text, reply_markup=keyboard)

    async def notify_unmatched_search(self, search: StudentSearch, student: User) -> None:
        budget_parts = []
        if search.budget_min is not None:
            budget_parts.append(str(search.budget_min))
        if search.budget_max is not None:
            budget_parts.append(str(search.budget_max))
        budget = "–".join(budget_parts) if budget_parts else "Не указан"

        text = (
            "Не найден репетитор:\n\n"
            f"Ученик: {format_user_display(student)}\n\n"
            f"Экзамен: {search.exam_keyword}\n"
            f"Цель: {search.goal}\n"
            f"Уровень: {search.current_level}\n"
            f"Бюджет: {budget}"
        )
        keyboard = build_contact_keyboard(student, "Написать ученику")
        await self._notify_admins(text, reply_markup=keyboard)
