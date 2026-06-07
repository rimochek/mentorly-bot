from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.reply import become_tutor_keyboard, main_menu_keyboard, tutor_cabinet_keyboard
from app.database.repositories.tutors import TutorRepository
from app.database.repositories.users import UserRepository

router = Router()


@router.message(F.text == "👤 Мой профиль")
async def my_profile(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Ошибка. Нажмите /start", reply_markup=main_menu_keyboard())
        return

    tutor_repo = TutorRepository(session)
    profile = await tutor_repo.get_by_user_id(user.id)

    if user.role == "tutor" and profile:
        await state.clear()
        await message.answer("Кабинет репетитора", reply_markup=tutor_cabinet_keyboard())
        return

    await message.answer(
        "У вас пока нет анкеты репетитора.",
        reply_markup=become_tutor_keyboard(),
    )
