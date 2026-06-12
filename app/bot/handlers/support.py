from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.reply import MAIN_MENU_BUTTONS, main_menu_keyboard
from app.bot.states.support import SupportStates
from app.database.repositories.users import UserRepository
from app.services.notifications import NotificationService
from app.services.analytics import EVENT_SUPPORT, track_event

router = Router()


@router.message(F.text == "🆘 Техподдержка")
async def start_support(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SupportStates.waiting_message)
    await message.answer(
        "Опишите вашу проблему или жалобу.\n"
        "Мы передадим обращение администратору.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(SupportStates.waiting_message)
async def process_support_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Ошибка. Нажмите /start", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    notifications = NotificationService(bot)
    await notifications.notify_support_complaint(user, message.text.strip())

    await track_event(
        message.from_user.id,
        EVENT_SUPPORT,
        "complaint_submitted",
        user_id=user.id,
    )

    await state.clear()
    await message.answer(
        "Ваше обращение отправлено ✅\n"
        "Администратор свяжется с вами при необходимости.",
        reply_markup=main_menu_keyboard(),
    )
