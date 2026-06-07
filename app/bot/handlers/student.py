import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import tutor_card_keyboard
from app.bot.keyboards.reply import (
    MAIN_MENU_BUTTONS,
    browse_keyboard,
    budget_keyboard,
    exam_keyboard,
    level_keyboard,
    main_menu_keyboard,
)
from app.bot.states.student import StudentSearchStates
from app.database.repositories.applications import ApplicationRepository
from app.database.repositories.searches import SearchRepository
from app.database.repositories.tutors import TutorRepository
from app.database.repositories.users import UserRepository
from app.services.notifications import NotificationService, build_contact_keyboard
from app.services.search import format_tutor_card, parse_budget, search_tutors

router = Router()
logger = logging.getLogger(__name__)

NO_MATCH_TEXT = (
    "По вашему запросу пока нет подходящих репетиторов. "
    "Мы получили заявку и можем подобрать вручную."
)


async def _get_browse_data(state: FSMContext) -> dict:
    data = await state.get_data()
    return {
        "tutor_ids": data.get("tutor_ids", []),
        "current_index": data.get("current_index", 0),
        "exam": data.get("exam", ""),
        "goal": data.get("goal", ""),
        "level": data.get("level", ""),
        "budget_text": data.get("budget_text", ""),
    }


async def _show_tutor_at_index(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    index: int,
) -> None:
    data = await _get_browse_data(state)
    tutor_ids: list[int] = data["tutor_ids"]

    if not tutor_ids or index >= len(tutor_ids):
        await state.clear()
        await message.answer("Больше репетиторов нет.", reply_markup=main_menu_keyboard())
        return

    tutor_repo = TutorRepository(session)
    tutor = await tutor_repo.get_by_id(tutor_ids[index])
    if not tutor:
        await message.answer("Репетитор не найден.", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    await state.update_data(current_index=index)
    card_text = format_tutor_card(tutor)
    keyboard = tutor_card_keyboard(tutor.id)

    if tutor.avatar_file_id:
        await message.answer_photo(
            photo=tutor.avatar_file_id,
            caption=card_text,
            reply_markup=keyboard,
        )
    else:
        await message.answer(card_text, reply_markup=keyboard)


@router.message(F.text == "🔎 Найти репетитора")
async def start_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(StudentSearchStates.exam)
    await message.answer(
        "К какому экзамену вы хотите подготовиться?",
        reply_markup=exam_keyboard(),
    )


@router.message(StudentSearchStates.exam)
async def process_exam(message: Message, state: FSMContext) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    exam = message.text.strip()
    if exam == "Другое":
        await message.answer("Напишите название экзамена:")
        return

    await state.update_data(exam=exam)
    await state.set_state(StudentSearchStates.goal)
    await message.answer(
        "Какую цель вы ставите?\n\n"
        "Примеры: IELTS 7.0+, SAT 1400+, Поступить в NU, Подтянуть математику",
        reply_markup=main_menu_keyboard(),
    )


@router.message(StudentSearchStates.goal)
async def process_goal(message: Message, state: FSMContext) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    await state.update_data(goal=message.text.strip())
    await state.set_state(StudentSearchStates.level)
    await message.answer(
        "Какой у вас текущий уровень?",
        reply_markup=level_keyboard(),
    )


@router.message(StudentSearchStates.level)
async def process_level(message: Message, state: FSMContext) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    await state.update_data(level=message.text.strip())
    await state.set_state(StudentSearchStates.budget)
    await message.answer(
        "Какой бюджет за одно занятие вы готовы выделить?",
        reply_markup=budget_keyboard(),
    )


@router.message(StudentSearchStates.budget)
async def process_budget(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    budget_text = message.text.strip()
    budget_min, budget_max = parse_budget(budget_text)
    data = await state.get_data()
    exam = data.get("exam", "")
    goal = data.get("goal", "")
    level = data.get("level", "")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Ошибка. Нажмите /start", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    search_repo = SearchRepository(session)
    search = await search_repo.create(
        user_id=user.id,
        exam_keyword=exam,
        goal=goal,
        current_level=level,
        budget_min=budget_min,
        budget_max=budget_max,
    )

    tutor_repo = TutorRepository(session)
    tutors = await tutor_repo.get_active_tutors()
    matched = search_tutors(tutors, exam, budget_min, budget_max)

    if not matched:
        await message.answer(NO_MATCH_TEXT, reply_markup=main_menu_keyboard())
        notifications = NotificationService(bot)
        await notifications.notify_unmatched_search(search, user)
        await state.clear()
        return

    tutor_ids = [t.id for t in matched]
    await state.update_data(
        tutor_ids=tutor_ids,
        current_index=0,
        exam=exam,
        goal=goal,
        level=level,
        budget_text=budget_text,
    )
    await state.set_state(StudentSearchStates.browsing)
    await message.answer(
        "Мы нашли репетиторов! Смотрите анкеты:",
        reply_markup=browse_keyboard(),
    )
    await _show_tutor_at_index(message, session, state, 0)


@router.message(StudentSearchStates.browsing, F.text == "➡️ Следующий репетитор")
async def next_tutor_reply(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await _get_browse_data(state)
    next_index = data["current_index"] + 1
    await _show_tutor_at_index(message, session, state, next_index)


@router.callback_query(F.data == "next_tutor")
async def next_tutor_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    data = await _get_browse_data(state)
    next_index = data["current_index"] + 1
    await callback.answer()
    if callback.message:
        await _show_tutor_at_index(callback.message, session, state, next_index)


@router.callback_query(F.data.startswith("contact:"))
async def contact_tutor(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    tutor_id = int(callback.data.split(":")[1])
    data = await _get_browse_data(state)

    user_repo = UserRepository(session)
    student = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not student:
        await callback.answer("Ошибка. Нажмите /start", show_alert=True)
        return

    tutor_repo = TutorRepository(session)
    tutor = await tutor_repo.get_by_id(tutor_id)
    if not tutor or not tutor.user:
        await callback.answer("Репетитор не найден", show_alert=True)
        return

    app_repo = ApplicationRepository(session)
    application = await app_repo.create(
        student_id=student.id,
        tutor_id=tutor.id,
        exam_keyword=data["exam"],
        goal=data["goal"],
        current_level=data["level"],
        budget_text=data["budget_text"],
    )

    notifications = NotificationService(bot)
    await notifications.notify_new_application(application, student, tutor, tutor.user)

    reply_markup = build_contact_keyboard(tutor.user.username)
    await callback.message.answer(
        "Заявка отправлена ✅ Репетитор или администратор скоро свяжется с вами.",
        reply_markup=reply_markup,
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def browse_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer("Главное меню", reply_markup=main_menu_keyboard())
