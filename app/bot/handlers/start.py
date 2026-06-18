from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.reply import main_menu_keyboard
from app.bot.states.student import StudentSearchStates
from app.database.repositories.users import UserRepository
from app.services.analytics import EVENT_BROWSE, EVENT_START, track_event

router = Router()

HOW_IT_WORKS_TEXT = (
    "ℹ️ Как это работает:\n\n"
    "1. Вы выбираете экзамен, уточняете цель (band, профиль ЕНТ, предмет AP и т.д.), уровень и бюджет.\n"
    "2. Бот показывает подходящих репетиторов по ключевым словам в описании.\n"
    "3. Вы можете отправить заявку репетитору.\n"
    "4. Репетитор создаёт анкету с описанием экзаменов, баллов, предметов и цен.\n\n"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    user_repo = UserRepository(session)
    user, is_new = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await user_repo.record_visit(user)
    await track_event(
        message.from_user.id,
        EVENT_START,
        "bot_start",
        user_id=user.id,
        properties={"is_new_user": is_new},
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
    current_state = await state.get_state()
    if current_state == StudentSearchStates.browsing.state:
        data = await state.get_data()
        cards_viewed = data.get("current_index", 0) + 1
        await track_event(
            message.from_user.id,
            EVENT_BROWSE,
            "browse_end",
            properties={"reason": "main_menu", "cards_viewed": cards_viewed},
        )
    await state.clear()
    await message.answer("Главное меню", reply_markup=main_menu_keyboard())
