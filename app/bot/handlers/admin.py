import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.admin import AdminFilter
from app.bot.keyboards.admin import (
    admin_moderation_keyboard,
    admin_moderation_status_label,
    admin_panel_keyboard,
    admin_profiles_filter_keyboard,
)
from app.bot.states.admin import AdminBroadcastStates, AdminModerationStates
from app.constants.text_limits import BROADCAST_MESSAGE_MAX, format_length_error, is_within_limit
from app.database.repositories.analytics import AnalyticsRepository
from app.database.repositories.tutors import (
    MODERATION_APPROVED,
    MODERATION_HIDDEN,
    MODERATION_REJECTED,
    TutorRepository,
)
from app.database.repositories.users import UserRepository
from app.services.analytics import format_admin_stats
from app.services.broadcast import AUDIENCE_LABELS, send_broadcast
from app.services.tutor_card import send_tutor_card

router = Router()
logger = logging.getLogger(__name__)


def _format_profiles_summary(counts: dict[str, int]) -> str:
    return (
        "Модерация анкет\n\n"
        f"Всего: {counts['total']}\n"
        f"Одобрено: {counts['approved']}\n"
        f"Скрыто: {counts['hidden']}\n"
        f"Отклонено: {counts['rejected']}\n"
        f"Verified Mentor: {counts['verified']}\n\n"
        "Выберите фильтр для просмотра:"
    )


async def _get_browse_data(state: FSMContext) -> dict:
    data = await state.get_data()
    return {
        "tutor_ids": data.get("tutor_ids", []),
        "current_index": data.get("current_index", 0),
        "filter_type": data.get("filter_type", "all"),
    }


async def _notify_tutor_moderation(bot: Bot, tutor, message_text: str) -> None:
    if not tutor.user:
        return
    try:
        await bot.send_message(tutor.user.telegram_id, message_text)
    except Exception:
        logger.exception("Failed to notify tutor %s about moderation", tutor.id)


async def _show_admin_tutor_at_index(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    index: int,
    bot: Bot,
) -> None:
    data = await _get_browse_data(state)
    tutor_ids: list[int] = data["tutor_ids"]

    if not tutor_ids or index >= len(tutor_ids):
        await state.clear()
        await message.answer("Больше нет анкет по выбранному фильтру.")
        return

    tutor_repo = TutorRepository(session)
    tutor = await tutor_repo.get_by_id(tutor_ids[index])
    if not tutor:
        await message.answer("Анкета не найдена.")
        await state.clear()
        return

    await state.update_data(current_index=index)
    status = admin_moderation_status_label(tutor)
    verified = "да" if tutor.is_verified else "нет"
    header = (
        f"Анкета {index + 1} из {len(tutor_ids)}\n"
        f"Статус: {status} | Verified: {verified}\n\n"
    )
    await message.answer(header)
    keyboard = admin_moderation_keyboard(tutor, tutor.user)
    await send_tutor_card(message, tutor, reply_markup=keyboard, session=session)


async def _start_browse(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    filter_type: str,
    bot: Bot,
) -> None:
    tutor_repo = TutorRepository(session)
    tutors = await tutor_repo.get_all_ordered(filter_type)
    if not tutors:
        await message.answer("Нет анкет по выбранному фильтру.")
        return

    tutor_ids = [t.id for t in tutors]
    await state.update_data(tutor_ids=tutor_ids, current_index=0, filter_type=filter_type)
    await state.set_state(AdminModerationStates.browsing)
    await _show_admin_tutor_at_index(message, session, state, 0, bot)


async def _send_admin_panel(message: Message) -> None:
    await message.answer(
        "Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=admin_panel_keyboard(),
    )


@router.message(Command("admin"), AdminFilter())
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _send_admin_panel(message)


@router.message(Command("stats"), AdminFilter())
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    repo = AnalyticsRepository(session)
    stats = await repo.get_admin_stats()
    await message.answer(format_admin_stats(stats))


@router.message(Command("profiles"), AdminFilter())
async def cmd_profiles(message: Message, session: AsyncSession) -> None:
    tutor_repo = TutorRepository(session)
    counts = await tutor_repo.get_moderation_counts()
    await message.answer(_format_profiles_summary(counts), reply_markup=admin_profiles_filter_keyboard())


@router.callback_query(F.data == "adm:stats", AdminFilter())
async def admin_panel_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    repo = AnalyticsRepository(session)
    stats = await repo.get_admin_stats()
    await callback.answer()
    await callback.message.answer(format_admin_stats(stats))


@router.callback_query(F.data == "adm:profiles", AdminFilter())
async def admin_panel_profiles(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    tutor_repo = TutorRepository(session)
    counts = await tutor_repo.get_moderation_counts()
    await callback.answer()
    await callback.message.answer(
        _format_profiles_summary(counts),
        reply_markup=admin_profiles_filter_keyboard(),
    )


@router.callback_query(F.data.startswith("adm:broadcast:"), AdminFilter())
async def admin_start_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    audience = callback.data.split(":")[2]
    if audience not in AUDIENCE_LABELS:
        await callback.answer("Неизвестная аудитория", show_alert=True)
        return

    await state.set_state(AdminBroadcastStates.waiting_message)
    await state.update_data(broadcast_audience=audience)
    await callback.answer()
    await callback.message.answer(
        f"Рассылка {AUDIENCE_LABELS[audience]}.\n\n"
        f"Отправьте текст сообщения (максимум {BROADCAST_MESSAGE_MAX} символов).\n"
        "Для отмены отправьте /admin",
    )


@router.message(AdminBroadcastStates.waiting_message, AdminFilter())
async def admin_send_broadcast(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("Отправьте текст сообщения.")
        return
    if not is_within_limit(text, BROADCAST_MESSAGE_MAX):
        await message.answer(format_length_error(BROADCAST_MESSAGE_MAX, len(text)))
        return

    data = await state.get_data()
    audience = data.get("broadcast_audience", "all")
    user_repo = UserRepository(session)
    telegram_ids = await user_repo.get_telegram_ids_by_audience(audience)

    if not telegram_ids:
        await state.clear()
        await message.answer("Нет получателей для выбранной аудитории.")
        return

    await message.answer(f"Рассылка началась… Получателей: {len(telegram_ids)}")
    sent, failed = await send_broadcast(bot, telegram_ids, text)
    await state.clear()
    await message.answer(
        f"Рассылка завершена.\n"
        f"Отправлено: {sent}\n"
        f"Ошибок: {failed}",
        reply_markup=admin_panel_keyboard(),
    )


@router.callback_query(F.data.startswith("adm:filter:"), AdminFilter())
async def admin_filter_profiles(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    filter_type = callback.data.split(":")[2]
    await callback.answer()
    await _start_browse(callback.message, state, session, filter_type, bot)


@router.callback_query(F.data.startswith("adm:view:"), AdminFilter())
async def admin_view_tutor(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    tutor_id = int(callback.data.split(":")[2])
    tutor_repo = TutorRepository(session)
    tutor = await tutor_repo.get_by_id(tutor_id)
    if not tutor:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    await state.update_data(tutor_ids=[tutor_id], current_index=0, filter_type="single")
    await state.set_state(AdminModerationStates.browsing)
    await callback.answer()
    await _show_admin_tutor_at_index(callback.message, session, state, 0, bot)


@router.callback_query(AdminModerationStates.browsing, F.data == "adm:next", AdminFilter())
async def admin_next_tutor(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    if not callback.message:
        await callback.answer()
        return

    data = await _get_browse_data(state)
    next_index = data["current_index"] + 1
    await callback.answer()
    await _show_admin_tutor_at_index(callback.message, session, state, next_index, bot)


@router.callback_query(F.data.startswith("adm:hide:"), AdminFilter())
async def admin_hide_tutor(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    await _apply_moderation_action(
        callback,
        session,
        state,
        bot,
        MODERATION_HIDDEN,
        "Ваша анкета скрыта модератором. Если это ошибка — напишите в техподдержку.",
        "Анкета скрыта.",
    )


@router.callback_query(F.data.startswith("adm:reject:"), AdminFilter())
async def admin_reject_tutor(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    await _apply_moderation_action(
        callback,
        session,
        state,
        bot,
        MODERATION_REJECTED,
        "Ваша анкета отклонена модератором. Если это ошибка — напишите в техподдержку.",
        "Анкета отклонена.",
    )


@router.callback_query(F.data.startswith("adm:restore:"), AdminFilter())
async def admin_restore_tutor(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    await _apply_moderation_action(
        callback,
        session,
        state,
        bot,
        MODERATION_APPROVED,
        "Ваша анкета снова доступна в поиске ✅",
        "Анкета восстановлена.",
    )


async def _apply_moderation_action(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    status: str,
    tutor_message: str,
    admin_message: str,
) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    tutor_id = int(callback.data.split(":")[2])
    tutor_repo = TutorRepository(session)
    tutor = await tutor_repo.get_by_id(tutor_id)
    if not tutor:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    previous_status = tutor.moderation_status
    await tutor_repo.set_moderation_status(tutor, status)
    if status != MODERATION_APPROVED and previous_status == MODERATION_APPROVED:
        await _notify_tutor_moderation(bot, tutor, tutor_message)
    elif status == MODERATION_APPROVED and previous_status != MODERATION_APPROVED:
        await _notify_tutor_moderation(bot, tutor, tutor_message)

    await callback.answer(admin_message)
    data = await _get_browse_data(state)
    current_index = data.get("current_index", 0)
    if await state.get_state() == AdminModerationStates.browsing.state:
        await _show_admin_tutor_at_index(callback.message, session, state, current_index, bot)


@router.callback_query(F.data.startswith("adm:verify:"), AdminFilter())
async def admin_verify_tutor(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    tutor_id = int(callback.data.split(":")[2])
    tutor_repo = TutorRepository(session)
    tutor = await tutor_repo.get_by_id(tutor_id)
    if not tutor:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    tutor = await tutor_repo.toggle_verified(tutor)
    if tutor.is_verified:
        await _notify_tutor_moderation(
            bot,
            tutor,
            "Вам выдан статус ✅ Verified Mentor! Теперь у вас есть приоритет при поиске подходящих репетиторов.",
        )
        await callback.answer("Verified Mentor выдан.")
    else:
        await callback.answer("Verified Mentor снят.")

    data = await _get_browse_data(state)
    current_index = data.get("current_index", 0)
    if await state.get_state() == AdminModerationStates.browsing.state:
        await _show_admin_tutor_at_index(callback.message, session, state, current_index, bot)
