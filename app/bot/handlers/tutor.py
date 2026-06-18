import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import edit_profile_keyboard
from app.bot.keyboards.reply import (
    SKIP_PHOTO,
    city_keyboard,
    main_menu_keyboard,
    skip_photo_keyboard,
    tutor_cabinet_keyboard,
)
from app.bot.states.tutor import TutorEditStates, TutorRegistrationStates
from app.database.repositories.tutors import TutorRepository, MODERATION_APPROVED
from app.database.repositories.users import UserRepository
from app.services.geocoding import get_city_from_coordinates
from app.services.notifications import NotificationService
from app.services.analytics import EVENT_SUPPORT, EVENT_TUTOR, track_event
from app.services.tutor_card import format_moderation_status, send_tutor_card
from app.constants.text_limits import (
    CITY_MAX,
    NAME_MAX,
    PLACE_OF_STUDY_MAX,
    TUTOR_DESCRIPTION_MAX,
    format_length_error,
    is_within_limit,
)
from app.services.tutor_stats import format_tutor_stats

router = Router()
logger = logging.getLogger(__name__)

DESCRIPTION_PROMPT = (
    "Напишите описание анкеты. Укажите:\n\n"
    "• какие экзамены вы ведёте\n"
    "• свои результаты\n"
    "• опыт\n"
    "• формат занятий\n"
    "• о себе\n\n"
    "Чтобы ученики находили вас в поиске, используйте ключевые слова экзаменов: "
    "IELTS, SAT, TOEFL, ЕНТ, NUET, AP, NIS, РФМШ, олимпиада и др.\n"
    "Например: «Готовлю к IELTS», «Подготовка к SAT», «ЕНТ физмат», «Готовлю к РФМШ».\n\n"
    "Пример описания:\n"
    "Готовлю к IELTS, SAT и ЕНТ (физмат). IELTS 8.0, SAT 1500. Учусь в NU. "
    "Помогаю с Writing, Speaking и математикой. Занятия онлайн.\n\n"
    f"Максимум {TUTOR_DESCRIPTION_MAX} символов."
)

EDIT_FIELD_PROMPTS = {
    "name": "Введите новое имя:",
    "age": "Введите новый возраст (число):",
    "city": (
        "В каком городе вы проживаете?\n\n"
        "Напишите название города или отправьте местоположение кнопкой ниже."
    ),
    "place_of_study": "Укажите новое место учёбы:",
    "price_min": "Укажите новую минимальную цену за занятие (число):",
    "price_max": "Укажите новую максимальную цену за занятие (число):",
    "description": DESCRIPTION_PROMPT,
}


async def _show_tutor_card(message: Message, session: AsyncSession, telegram_id: int) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        await message.answer("Ошибка. Нажмите /start", reply_markup=main_menu_keyboard())
        return

    tutor_repo = TutorRepository(session)
    profile = await tutor_repo.get_by_user_id(user.id)
    if not profile:
        await message.answer("Анкета не найдена.", reply_markup=main_menu_keyboard())
        return

    moderation_line = format_moderation_status(profile)
    if moderation_line:
        await message.answer(moderation_line)

    await send_tutor_card(message, profile, session=session)


@router.message(F.text == "🧑‍🏫 Стать репетитором")
async def become_tutor(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Ошибка. Нажмите /start", reply_markup=main_menu_keyboard())
        return

    tutor_repo = TutorRepository(session)
    profile = await tutor_repo.get_by_user_id(user.id)
    if profile:
        await message.answer("Кабинет репетитора", reply_markup=tutor_cabinet_keyboard())
        return

    await state.set_state(TutorRegistrationStates.name)
    await message.answer("Введите ваше имя:", reply_markup=main_menu_keyboard())


@router.message(TutorRegistrationStates.name)
async def reg_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not is_within_limit(name, NAME_MAX):
        await message.answer(format_length_error(NAME_MAX, len(name)))
        return
    await state.update_data(name=name)
    await state.set_state(TutorRegistrationStates.age)
    await message.answer("Введите ваш возраст:")


@router.message(TutorRegistrationStates.age)
async def reg_age(message: Message, state: FSMContext) -> None:
    try:
        age = int(message.text.strip())
    except ValueError:
        await message.answer("Введите возраст числом:")
        return
    await state.update_data(age=age)
    await state.set_state(TutorRegistrationStates.city)
    await message.answer(
        "В каком городе вы проживаете?\n\n"
        "Напишите название города или отправьте местоположение кнопкой ниже.",
        reply_markup=city_keyboard(),
    )


async def _proceed_after_city(message: Message, state: FSMContext, city: str) -> None:
    if not is_within_limit(city, CITY_MAX):
        await message.answer(format_length_error(CITY_MAX, len(city.strip())))
        return
    await state.update_data(city=city.strip())
    await state.set_state(TutorRegistrationStates.place_of_study)
    await message.answer(
        "Укажите место учёбы:",
        reply_markup=main_menu_keyboard(),
    )


@router.message(TutorRegistrationStates.city, F.location)
async def reg_city_location(message: Message, state: FSMContext) -> None:
    if not message.location:
        return

    city = await get_city_from_coordinates(
        message.location.latitude,
        message.location.longitude,
    )
    if not city:
        await message.answer(
            "Не удалось определить город по местоположению. "
            "Пожалуйста, введите название города вручную.",
            reply_markup=city_keyboard(),
        )
        return

    await message.answer(f"Город определён: {city}")
    await _proceed_after_city(message, state, city)


@router.message(TutorRegistrationStates.city)
async def reg_city(message: Message, state: FSMContext) -> None:
    await _proceed_after_city(message, state, message.text.strip())


@router.message(TutorRegistrationStates.place_of_study)
async def reg_place(message: Message, state: FSMContext) -> None:
    place = message.text.strip()
    if not is_within_limit(place, PLACE_OF_STUDY_MAX):
        await message.answer(format_length_error(PLACE_OF_STUDY_MAX, len(place)))
        return
    await state.update_data(place_of_study=place)
    await state.set_state(TutorRegistrationStates.price_min)
    await message.answer("Укажите минимальную цену за занятие (в тенге):")


@router.message(TutorRegistrationStates.price_min)
async def reg_price_min(message: Message, state: FSMContext) -> None:
    try:
        price_min = int(message.text.strip())
    except ValueError:
        await message.answer("Введите цену числом:")
        return
    await state.update_data(price_min=price_min)
    await state.set_state(TutorRegistrationStates.price_max)
    await message.answer("Укажите максимальную цену за занятие (в тенге):")


@router.message(TutorRegistrationStates.price_max)
async def reg_price_max(message: Message, state: FSMContext) -> None:
    try:
        price_max = int(message.text.strip())
    except ValueError:
        await message.answer("Введите цену числом:")
        return
    await state.update_data(price_max=price_max)
    await state.set_state(TutorRegistrationStates.description)
    await message.answer(DESCRIPTION_PROMPT)


@router.message(TutorRegistrationStates.description)
async def reg_description(message: Message, state: FSMContext) -> None:
    description = message.text.strip()
    if not is_within_limit(description, TUTOR_DESCRIPTION_MAX):
        await message.answer(format_length_error(TUTOR_DESCRIPTION_MAX, len(description)))
        return
    await state.update_data(description=description)
    await state.set_state(TutorRegistrationStates.photo)
    await message.answer(
        "Отправьте фото профиля или нажмите «Пропустить».",
        reply_markup=skip_photo_keyboard(),
    )


@router.message(TutorRegistrationStates.photo, F.text == SKIP_PHOTO)
async def reg_skip_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    await _finish_registration(message, state, session, bot, avatar_file_id=None)


@router.message(TutorRegistrationStates.photo, F.photo)
async def reg_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    avatar_file_id = message.photo[-1].file_id
    await _finish_registration(message, state, session, bot, avatar_file_id=avatar_file_id)


@router.message(TutorRegistrationStates.photo)
async def reg_photo_invalid(message: Message) -> None:
    await message.answer(
        "Отправьте фото или нажмите «Пропустить».",
        reply_markup=skip_photo_keyboard(),
    )


async def _finish_registration(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    avatar_file_id: str | None,
) -> None:
    data = await state.get_data()
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Ошибка. Нажмите /start", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    tutor_repo = TutorRepository(session)
    profile = await tutor_repo.create(
        user_id=user.id,
        name=data["name"],
        age=data["age"],
        city=data["city"],
        place_of_study=data["place_of_study"],
        price_min=data["price_min"],
        price_max=data["price_max"],
        description=data["description"],
        avatar_file_id=avatar_file_id,
    )
    await user_repo.set_role(user, "tutor")

    notifications = NotificationService(bot)
    await notifications.notify_new_tutor_profile(profile, user)

    await track_event(
        message.from_user.id,
        EVENT_TUTOR,
        "profile_created",
        user_id=user.id,
        properties={"tutor_id": profile.id},
    )

    await state.clear()
    await message.answer(
        "Анкета создана ✅ Ученики смогут найти вас по ключевым словам в описании.",
        reply_markup=tutor_cabinet_keyboard(),
    )


@router.message(F.text == "👤 Моя анкета")
async def my_tutor_profile(message: Message, session: AsyncSession) -> None:
    await _show_tutor_card(message, session, message.from_user.id)


@router.message(F.text == "📊 Моя статистика")
async def my_tutor_stats(message: Message, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Ошибка. Нажмите /start", reply_markup=main_menu_keyboard())
        return

    tutor_repo = TutorRepository(session)
    profile = await tutor_repo.get_by_user_id(user.id)
    if not profile:
        await message.answer("Анкета не найдена.", reply_markup=main_menu_keyboard())
        return

    await message.answer(format_tutor_stats(profile), reply_markup=tutor_cabinet_keyboard())


@router.message(F.text == "✏️ Редактировать анкету")
async def edit_profile_menu(message: Message) -> None:
    await message.answer("Что вы хотите изменить?", reply_markup=edit_profile_keyboard())


@router.callback_query(F.data.startswith("edit:"))
async def edit_field_choice(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    field = callback.data.split(":")[1]
    if field == "back":
        await callback.answer()
        await callback.message.answer("Кабинет репетитора", reply_markup=tutor_cabinet_keyboard())
        return

    await state.update_data(edit_field=field)
    await state.set_state(TutorEditStates.waiting_value)
    await callback.answer()
    prompt = EDIT_FIELD_PROMPTS.get(field, "Введите новое значение:")
    reply_markup = city_keyboard() if field == "city" else None
    await callback.message.answer(prompt, reply_markup=reply_markup)


@router.message(TutorEditStates.waiting_value, F.location)
async def edit_city_location(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    if data.get("edit_field") != "city":
        await message.answer("Пожалуйста, введите значение текстом.")
        return
    if not message.location:
        return

    city = await get_city_from_coordinates(
        message.location.latitude,
        message.location.longitude,
    )
    if not city:
        await message.answer(
            "Не удалось определить город по местоположению. "
            "Пожалуйста, введите название города вручную.",
            reply_markup=city_keyboard(),
        )
        return

    await message.answer(f"Город определён: {city}")
    await _save_edited_field(message, state, session, "city", city)


@router.message(TutorEditStates.waiting_value)
async def edit_field_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    field = data.get("edit_field")
    if not field:
        await state.clear()
        await message.answer("Кабинет репетитора", reply_markup=tutor_cabinet_keyboard())
        return

    value: str | int = message.text.strip()
    field_limits = {
        "name": NAME_MAX,
        "city": CITY_MAX,
        "place_of_study": PLACE_OF_STUDY_MAX,
        "description": TUTOR_DESCRIPTION_MAX,
    }
    if field in field_limits and not is_within_limit(str(value), field_limits[field]):
        await message.answer(format_length_error(field_limits[field], len(str(value))))
        return
    if field in ("age", "price_min", "price_max"):
        try:
            value = int(value)
        except ValueError:
            await message.answer("Введите число:")
            return

    await _save_edited_field(message, state, session, field, value)


async def _save_edited_field(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    field: str,
    value: str | int,
) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Ошибка. Нажмите /start", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    tutor_repo = TutorRepository(session)
    profile = await tutor_repo.get_by_user_id(user.id)
    if not profile:
        await message.answer("Анкета не найдена.", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    await tutor_repo.update_field(profile, field, value)
    await state.clear()
    await message.answer("Сохранено ✅", reply_markup=tutor_cabinet_keyboard())


@router.message(F.text == "🖼 Изменить фото")
async def change_photo_start(message: Message, state: FSMContext) -> None:
    await state.set_state(TutorEditStates.photo)
    await message.answer("Отправьте новое фото профиля:")


@router.message(TutorEditStates.photo, F.photo)
async def change_photo_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    avatar_file_id = message.photo[-1].file_id
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Ошибка. Нажмите /start", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    tutor_repo = TutorRepository(session)
    profile = await tutor_repo.get_by_user_id(user.id)
    if not profile:
        await message.answer("Анкета не найдена.", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    await tutor_repo.update_field(profile, "avatar_file_id", avatar_file_id)
    await state.clear()
    await message.answer("Фото обновлено ✅", reply_markup=tutor_cabinet_keyboard())


@router.message(F.text == "👁 Включить/выключить анкету")
async def toggle_profile(message: Message, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Ошибка. Нажмите /start", reply_markup=main_menu_keyboard())
        return

    tutor_repo = TutorRepository(session)
    profile = await tutor_repo.get_by_user_id(user.id)
    if not profile:
        await message.answer("Анкета не найдена.", reply_markup=main_menu_keyboard())
        return

    profile = await tutor_repo.toggle_active(profile)
    status = "включена ✅" if profile.is_active else "выключена ⏸"
    text = f"Анкета {status}"
    if profile.moderation_status != MODERATION_APPROVED:
        text += "\n\nАнкета не отображается в поиске: действует решение модератора."
    elif profile.is_active:
        text += "\n\nАнкета видна ученикам в поиске."
    else:
        text += "\n\nАнкета скрыта из поиска (выключена вами)."
    await message.answer(text, reply_markup=tutor_cabinet_keyboard())
