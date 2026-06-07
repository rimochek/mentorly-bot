from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

MAIN_MENU_BUTTONS = [
    "🔎 Найти репетитора",
    "🧑‍🏫 Стать репетитором",
    "👤 Мой профиль",
    "ℹ️ Как это работает",
    "🆘 Техподдержка",
]

BROWSE_BUTTONS = [
    "➡️ Следующий репетитор",
    "🏠 Главное меню",
]

TUTOR_CABINET_BUTTONS = [
    "👤 Моя анкета",
    "✏️ Редактировать анкету",
    "🖼 Изменить фото",
    "👁 Включить/выключить анкету",
    "🏠 Главное меню",
]

SKIP_PHOTO = "Пропустить"
SHARE_LOCATION = "📍 Отправить местоположение"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn)] for btn in MAIN_MENU_BUTTONS],
        resize_keyboard=True,
    )


def browse_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn)] for btn in BROWSE_BUTTONS],
        resize_keyboard=True,
    )


def tutor_cabinet_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn)] for btn in TUTOR_CABINET_BUTTONS],
        resize_keyboard=True,
    )


def skip_photo_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=SKIP_PHOTO)]],
        resize_keyboard=True,
    )


def become_tutor_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧑‍🏫 Стать репетитором")],
            [KeyboardButton(text="🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


EXAM_BUTTONS = [
    "IELTS",
    "SAT",
    "TOEFL",
    "NUET",
    "ЕНТ",
    "AP",
    "NIS",
    "РФМШ",
    "Олимпиады",
    "Другое",
]

LEVEL_BUTTONS = [
    "Начинающий",
    "Средний",
    "Продвинутый",
    "Уже сдавал экзамен",
    "Не знаю",
]

BUDGET_BUTTONS = [
    "до 3000 ₸",
    "3000–5000 ₸",
    "5000–8000 ₸",
    "8000+ ₸",
    "Не знаю",
]


def _buttons_keyboard(buttons: list[str], columns: int = 2) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []
    for btn in buttons:
        row.append(KeyboardButton(text=btn))
        if len(row) == columns:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def exam_keyboard() -> ReplyKeyboardMarkup:
    return _buttons_keyboard(EXAM_BUTTONS, columns=2)


def level_keyboard() -> ReplyKeyboardMarkup:
    return _buttons_keyboard(LEVEL_BUTTONS, columns=2)


def budget_keyboard() -> ReplyKeyboardMarkup:
    return _buttons_keyboard(BUDGET_BUTTONS, columns=2)


def city_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SHARE_LOCATION, request_location=True)],
        ],
        resize_keyboard=True,
    )
