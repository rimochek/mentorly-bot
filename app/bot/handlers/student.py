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
from app.services.notifications import NotificationService
from app.services.analytics import (
    EVENT_BROWSE,
    EVENT_CONTACT,
    EVENT_SEARCH,
    track_event,
)
from app.services.user_contact import build_contact_keyboard
from app.constants.text_limits import (
    EXAM_CUSTOM_MAX,
    GOAL_CUSTOM_MAX,
    format_length_error,
    is_within_limit,
)
from app.services.search import parse_budget, search_tutors
from app.services.search_config import (
    OLYMPIAD_GRADES,
    OLYMPIAD_SUBJECTS,
    build_olympiad_goal,
    exam_detail_keyboard,
    get_exam_detail_prompt,
    is_ap_custom_goal,
    olympiad_grade_keyboard,
    olympiad_subject_keyboard,
    resolve_exam_detail,
    skips_goal_step,
)
from app.services.tutor_card import send_tutor_card
from app.services.tutor_stats import increment_tutor_contact, increment_tutor_view

router = Router()
logger = logging.getLogger(__name__)

NO_MATCH_TEXT = (
    "По вашему запросу пока нет подходящих репетиторов. "
    "Мы получили заявку и можем подобрать вручную."
)
FALLBACK_INTRO_ALL = (
    "Точных совпадений не нашлось. Ниже — репетиторы по смежным предметам."
)
FALLBACK_INTRO_PARTIAL = "Дальше — репетиторы по смежным предметам."


async def _get_browse_data(state: FSMContext) -> dict:
    data = await state.get_data()
    return {
        "tutor_ids": data.get("tutor_ids", []),
        "current_index": data.get("current_index", 0),
        "fallback_start_index": data.get("fallback_start_index"),
        "exam": data.get("exam", ""),
        "goal": data.get("goal", ""),
        "level": data.get("level", ""),
        "budget_text": data.get("budget_text", ""),
    }


async def _go_to_level(message: Message, state: FSMContext, goal: str) -> None:
    await state.update_data(goal=goal)
    await state.set_state(StudentSearchStates.level)
    await message.answer(
        "Какой у вас текущий уровень?",
        reply_markup=level_keyboard(),
    )


async def _track_browse_end(telegram_id: int, reason: str, cards_viewed: int) -> None:
    await track_event(
        telegram_id,
        EVENT_BROWSE,
        "browse_end",
        properties={"reason": reason, "cards_viewed": cards_viewed},
    )


async def _show_tutor_at_index(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    index: int,
) -> None:
    data = await _get_browse_data(state)
    tutor_ids: list[int] = data["tutor_ids"]

    if not tutor_ids or index >= len(tutor_ids):
        if tutor_ids and index >= len(tutor_ids):
            await _track_browse_end(message.from_user.id, "exhausted", len(tutor_ids))
        await state.clear()
        await message.answer("По данным запросам больше нету репетиторов.\nПриходите позже, список обновляется ежедневно!", reply_markup=main_menu_keyboard())
        return

    fallback_start = data.get("fallback_start_index")
    if fallback_start is not None and index == fallback_start and fallback_start > 0:
        await message.answer(FALLBACK_INTRO_PARTIAL)

    tutor_repo = TutorRepository(session)
    tutor = await tutor_repo.get_by_id(tutor_ids[index])
    if not tutor:
        await message.answer("Репетитор не найден.", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    await state.update_data(current_index=index)
    keyboard = tutor_card_keyboard(tutor.id)
    await send_tutor_card(message, tutor, reply_markup=keyboard, session=session)
    await increment_tutor_view(session, tutor.id)
    await track_event(
        message.from_user.id,
        EVENT_BROWSE,
        "tutor_viewed",
        properties={"tutor_id": tutor.id, "index": index, "total": len(tutor_ids)},
    )


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
        await state.set_state(StudentSearchStates.custom_exam_name)
        await message.answer("Напишите название экзамена:")
        return

    await state.update_data(exam=exam)

    if skips_goal_step(exam):
        await _go_to_level(message, state, exam)
        return

    if exam == "Олимпиады":
        await state.set_state(StudentSearchStates.olympiad_subject)
        await message.answer(
            "Выберите предмет олимпиады:",
            reply_markup=olympiad_subject_keyboard(),
        )
        return

    keyboard = exam_detail_keyboard(exam)
    if keyboard is None:
        await state.set_state(StudentSearchStates.custom_goal)
        await message.answer(
            "Кратко укажите цель подготовки:",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.set_state(StudentSearchStates.exam_detail)
    await message.answer(get_exam_detail_prompt(exam), reply_markup=keyboard)


@router.message(StudentSearchStates.custom_exam_name)
async def process_custom_exam_name(message: Message, state: FSMContext) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    exam = message.text.strip()
    if not exam:
        await message.answer("Введите название экзамена:")
        return
    if not is_within_limit(exam, EXAM_CUSTOM_MAX):
        await message.answer(format_length_error(EXAM_CUSTOM_MAX, len(exam)))
        return

    await state.update_data(exam=exam)
    await state.set_state(StudentSearchStates.custom_goal)
    await message.answer(
        "Кратко укажите цель подготовки:",
        reply_markup=main_menu_keyboard(),
    )


@router.message(StudentSearchStates.exam_detail)
async def process_exam_detail(message: Message, state: FSMContext) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    data = await state.get_data()
    exam = data.get("exam", "")
    goal = resolve_exam_detail(exam, message.text or "")
    if goal is None:
        await message.answer("Выберите вариант из списка на клавиатуре.")
        return

    if is_ap_custom_goal(goal):
        await state.set_state(StudentSearchStates.ap_custom)
        await message.answer(
            "Напишите предмет AP:",
            reply_markup=main_menu_keyboard(),
        )
        return

    await _go_to_level(message, state, goal)


@router.message(StudentSearchStates.ap_custom)
async def process_ap_custom(message: Message, state: FSMContext) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    goal = message.text.strip()
    if not goal:
        await message.answer("Напишите предмет AP:")
        return
    if not is_within_limit(goal, GOAL_CUSTOM_MAX):
        await message.answer(format_length_error(GOAL_CUSTOM_MAX, len(goal)))
        return

    await _go_to_level(message, state, f"AP {goal}")


@router.message(StudentSearchStates.custom_goal)
async def process_custom_goal(message: Message, state: FSMContext) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    goal = message.text.strip()
    if not goal:
        await message.answer("Укажите цель подготовки:")
        return
    if not is_within_limit(goal, GOAL_CUSTOM_MAX):
        await message.answer(format_length_error(GOAL_CUSTOM_MAX, len(goal)))
        return

    await _go_to_level(message, state, goal)


@router.message(StudentSearchStates.olympiad_subject)
async def process_olympiad_subject(message: Message, state: FSMContext) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    subject = message.text.strip()
    if subject not in OLYMPIAD_SUBJECTS:
        await message.answer("Выберите предмет из списка на клавиатуре.")
        return

    await state.update_data(olympiad_subject=subject)
    await state.set_state(StudentSearchStates.olympiad_grade)
    await message.answer(
        "Выберите класс:",
        reply_markup=olympiad_grade_keyboard(),
    )


@router.message(StudentSearchStates.olympiad_grade)
async def process_olympiad_grade(message: Message, state: FSMContext) -> None:
    if message.text in MAIN_MENU_BUTTONS:
        return

    grade = message.text.strip()
    if grade not in OLYMPIAD_GRADES:
        await message.answer("Выберите класс из списка на клавиатуре.")
        return

    data = await state.get_data()
    subject = data.get("olympiad_subject", "")
    goal = build_olympiad_goal(subject, grade)
    await _go_to_level(message, state, goal)


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
    matched, primary_count = search_tutors(tutors, exam, budget_min, budget_max, goal=goal)

    if not matched:
        await track_event(
            message.from_user.id,
            EVENT_SEARCH,
            "search_no_match",
            user_id=user.id,
            properties={
                "exam": exam,
                "goal": goal,
                "level": level,
                "budget_text": budget_text,
                "search_id": search.id,
                "matched_count": 0,
            },
        )
        await message.answer(NO_MATCH_TEXT, reply_markup=main_menu_keyboard())
        notifications = NotificationService(bot)
        await notifications.notify_unmatched_search(search, user)
        await state.clear()
        return

    tutor_ids = [t.id for t in matched]
    fallback_start_index = primary_count if primary_count < len(matched) else None
    await track_event(
        message.from_user.id,
        EVENT_SEARCH,
        "search_completed",
        user_id=user.id,
        properties={
            "exam": exam,
            "goal": goal,
            "level": level,
            "budget_text": budget_text,
            "search_id": search.id,
            "matched_count": len(tutor_ids),
            "primary_count": primary_count,
            "fallback_count": len(tutor_ids) - primary_count,
        },
    )
    await state.update_data(
        tutor_ids=tutor_ids,
        current_index=0,
        fallback_start_index=fallback_start_index,
        exam=exam,
        goal=goal,
        level=level,
        budget_text=budget_text,
    )
    await state.set_state(StudentSearchStates.browsing)
    intro_text = "Мы нашли репетиторов! Смотрите анкеты:"
    if fallback_start_index == 0:
        intro_text = FALLBACK_INTRO_ALL
    elif fallback_start_index is not None:
        intro_text = "Мы нашли репетиторов! Сначала — точные совпадения, ниже — по смежным предметам."
    await message.answer(
        intro_text,
        reply_markup=browse_keyboard(),
    )
    await _show_tutor_at_index(message, session, state, 0)


@router.message(StudentSearchStates.browsing, F.text == "➡️ Следующий репетитор")
async def next_tutor_reply(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await _get_browse_data(state)
    next_index = data["current_index"] + 1
    await track_event(
        message.from_user.id,
        EVENT_BROWSE,
        "browse_next",
        properties={"index": next_index},
    )
    await _show_tutor_at_index(message, session, state, next_index)


@router.callback_query(F.data == "next_tutor")
async def next_tutor_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    data = await _get_browse_data(state)
    next_index = data["current_index"] + 1
    await callback.answer()
    if callback.from_user:
        await track_event(
            callback.from_user.id,
            EVENT_BROWSE,
            "browse_next",
            properties={"index": next_index},
        )
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

    await increment_tutor_contact(session, tutor.id, callback.from_user.id)

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

    await track_event(
        callback.from_user.id,
        EVENT_CONTACT,
        "application_sent",
        user_id=student.id,
        properties={"tutor_id": tutor.id, "application_id": application.id},
    )

    reply_markup = build_contact_keyboard(tutor.user, "Открыть чат с репетитором")
    confirmation_text = (
        "Заявка отправлена ✅ Репетитор или администратор скоро свяжется с вами."
    )
    if not tutor.user.username:
        confirmation_text += (
            "\n\nЕсли кнопка не открывает чат, репетитор или администратор "
            "свяжется с вами через бота."
        )
    await callback.message.answer(
        confirmation_text,
        reply_markup=reply_markup,
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def browse_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user:
        data = await state.get_data()
        cards_viewed = data.get("current_index", 0) + 1
        await _track_browse_end(callback.from_user.id, "main_menu", cards_viewed)
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer("Главное меню", reply_markup=main_menu_keyboard())
