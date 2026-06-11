from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.reply import main_menu_keyboard
from app.database.repositories.users import UserRepository

router = Router()

HOW_IT_WORKS_TEXT = (
    "ℹ️ Как это работает:\n\n"
    "1. Вы выбираете экзамен, цель, уровень и бюджет.\n"
    "2. Бот показывает подходящих репетиторов по ключевым словам в описании.\n"
    "3. Вы можете отправить заявку репетитору.\n"
    "4. Репетитор создаёт анкету с описанием экзаменов, опыта и цен.\n\n"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    user_repo = UserRepository(session)
    await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(
        'Привет! Я помогу найти репетитора для подготовки к экзаменам. Нажмите кнопку "🔎 Найти репетитора", чтобы начать поиск!',
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == "ℹ️ Как это работает")
async def how_it_works(message: Message) -> None:
    await message.answer(HOW_IT_WORKS_TEXT, reply_markup=main_menu_keyboard())


@router.message(F.text == "🏠 Главное меню")
async def go_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=main_menu_keyboard())
