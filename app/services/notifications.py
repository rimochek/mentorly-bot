import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import get_settings
from app.database.models import Application, StudentSearch, TutorProfile, User

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.admin_ids = get_settings().admin_id_list

    async def _notify_admins(self, text: str) -> None:
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(admin_id, text)
            except Exception:
                logger.exception("Failed to notify admin %s", admin_id)

    def _format_user(self, user: User) -> str:
        if user.username:
            return f"@{user.username}"
        if user.full_name:
            return user.full_name
        return f"ID {user.telegram_id}"

    async def notify_new_tutor_profile(self, profile: TutorProfile, user: User) -> None:
        text = (
            "Новая анкета репетитора:\n\n"
            f"{profile.name}\n"
            f"{profile.city}\n"
            f"{profile.place_of_study}\n"
            f"{profile.price_min}–{profile.price_max} ₸\n"
            f"{profile.description}\n"
            f"{self._format_user(user)}"
        )
        await self._notify_admins(text)

    async def notify_new_application(
        self,
        application: Application,
        student: User,
        tutor_profile: TutorProfile,
        tutor_user: User,
    ) -> None:
        admin_text = (
            "Новая заявка:\n\n"
            f"Student: {self._format_user(student)}\n"
            f"Tutor: {tutor_profile.name} ({self._format_user(tutor_user)})\n"
            f"Exam: {application.exam_keyword}\n"
            f"Goal: {application.goal}\n"
            f"Level: {application.current_level}\n"
            f"Budget: {application.budget_text}"
        )
        await self._notify_admins(admin_text)

        tutor_text = (
            "У тебя новая заявка 👀\n\n"
            f"Ученик: {self._format_user(student)}\n"
            f"Экзамен: {application.exam_keyword}\n"
            f"Цель: {application.goal}\n"
            f"Уровень: {application.current_level}\n"
            f"Бюджет: {application.budget_text}"
        )
        if student.username:
            tutor_text += f"\n\nКонтакт: https://t.me/{student.username}"

        try:
            await self.bot.send_message(tutor_user.telegram_id, tutor_text)
        except Exception:
            logger.exception("Failed to notify tutor %s", tutor_user.telegram_id)

    def _format_user_contact(self, user: User) -> str:
        contact = self._format_user(user)
        if user.username:
            contact += f"\nhttps://t.me/{user.username}"
        else:
            contact += f"\ntg://user?id={user.telegram_id}"
        return contact

    async def notify_support_complaint(self, user: User, text: str) -> None:
        admin_text = (
            "🆘 Обращение в техподдержку:\n\n"
            f"Пользователь: {self._format_user_contact(user)}\n\n"
            f"Сообщение:\n{text}"
        )
        await self._notify_admins(admin_text)

    async def notify_unmatched_search(self, search: StudentSearch, student: User) -> None:
        budget_parts = []
        if search.budget_min is not None:
            budget_parts.append(str(search.budget_min))
        if search.budget_max is not None:
            budget_parts.append(str(search.budget_max))
        budget = "–".join(budget_parts) if budget_parts else "Не указан"

        text = (
            "Не найден репетитор:\n\n"
            f"Student: {self._format_user(student)}\n"
            f"Exam: {search.exam_keyword}\n"
            f"Goal: {search.goal}\n"
            f"Level: {search.current_level}\n"
            f"Budget: {budget}"
        )
        await self._notify_admins(text)


def build_contact_keyboard(tutor_username: str | None) -> InlineKeyboardMarkup | None:
    if not tutor_username:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть чат с репетитором", url=f"https://t.me/{tutor_username}")]
        ]
    )
