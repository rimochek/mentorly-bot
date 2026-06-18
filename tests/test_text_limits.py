from app.constants.text_limits import (
    GOAL_CUSTOM_MAX,
    TUTOR_DESCRIPTION_MAX,
    format_length_error,
    is_within_limit,
)


def test_is_within_limit() -> None:
    assert is_within_limit("hello", 5) is True
    assert is_within_limit("hello!", 5) is False


def test_format_length_error() -> None:
    message = format_length_error(100, 150)
    assert "100" in message
    assert "150" in message
    assert "лимит" in message.lower()


def test_description_limit_is_1500() -> None:
    assert TUTOR_DESCRIPTION_MAX == 1500
    assert is_within_limit("x" * 1500, TUTOR_DESCRIPTION_MAX) is True
    assert is_within_limit("x" * 1501, TUTOR_DESCRIPTION_MAX) is False
