from app.database.models import User
from app.services.user_contact import (
    build_contact_keyboard,
    build_dual_contact_keyboard,
    format_contact_line,
    format_user_display,
    get_contact_url,
)


def _make_user(**kwargs) -> User:
    defaults = {
        "id": 1,
        "telegram_id": 123456789,
        "username": None,
        "full_name": "Иван Иванов",
        "role": None,
    }
    defaults.update(kwargs)
    return User(**defaults)


class TestGetContactUrl:
    def test_with_username(self) -> None:
        user = _make_user(username="ivan")
        assert get_contact_url(user) == "https://t.me/ivan"

    def test_without_username(self) -> None:
        user = _make_user(username=None, telegram_id=987654321)
        assert get_contact_url(user) == "tg://user?id=987654321"


class TestFormatContactLine:
    def test_shows_username(self) -> None:
        user = _make_user(username="ivan")
        assert format_contact_line(user) == "@ivan"

    def test_shows_full_name_without_username(self) -> None:
        user = _make_user(username=None, full_name="Иван", telegram_id=111222333)
        assert format_contact_line(user) == "Иван"
        assert "111222333" not in format_contact_line(user)


class TestFormatUserDisplay:
    def test_username_only(self) -> None:
        assert format_user_display(_make_user(username="test")) == "@test"

    def test_full_name_without_username(self) -> None:
        user = _make_user(username=None, full_name="Anna", telegram_id=555)
        assert format_user_display(user) == "Anna"

    def test_fallback_without_name(self) -> None:
        user = _make_user(username=None, full_name=None)
        assert format_user_display(user) == "Пользователь"


class TestBuildContactKeyboard:
    def test_always_has_one_button(self) -> None:
        user = _make_user(username=None)
        keyboard = build_contact_keyboard(user, "Написать")
        assert len(keyboard.inline_keyboard) == 1
        assert keyboard.inline_keyboard[0][0].url == "tg://user?id=123456789"

    def test_button_uses_tme_for_username(self) -> None:
        user = _make_user(username="tutor1")
        keyboard = build_contact_keyboard(user, "Открыть чат")
        assert keyboard.inline_keyboard[0][0].url == "https://t.me/tutor1"


class TestBuildDualContactKeyboard:
    def test_has_two_buttons(self) -> None:
        student = _make_user(username="student1")
        tutor = _make_user(username="tutor1", telegram_id=999)
        keyboard = build_dual_contact_keyboard(
            student,
            "Написать ученику",
            tutor,
            "Написать репетитору",
        )
        assert len(keyboard.inline_keyboard) == 2
