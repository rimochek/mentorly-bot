from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

EDIT_FIELDS = [
    ("name", "Имя"),
    ("age", "Возраст"),
    ("city", "Город"),
    ("place_of_study", "Место учебы"),
    ("price_min", "Цена от"),
    ("price_max", "Цена до"),
    ("description", "Описание"),
]


def tutor_card_keyboard(tutor_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📩 Связаться", callback_data=f"contact:{tutor_id}"),
                InlineKeyboardButton(text="➡️ Следующий", callback_data="next_tutor"),
            ],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")],
        ]
    )


def edit_profile_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"edit:{field}")]
        for field, label in EDIT_FIELDS
    ]
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="edit:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
