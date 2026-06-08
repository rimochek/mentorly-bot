from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramBadRequest

from app.services.tutor_card import (
    TELEGRAM_CAPTION_MAX,
    TELEGRAM_MESSAGE_MAX,
    format_tutor_card,
    send_tutor_card,
    truncate_text,
)

from tests.conftest import make_tutor


class TestTruncateText:
    def test_short_text_unchanged(self) -> None:
        assert truncate_text("hello", 10) == "hello"

    def test_long_text_truncated(self) -> None:
        assert truncate_text("a" * 20, 10) == "a" * 9 + "…"


class TestFormatTutorCard:
    def test_long_description_card(self) -> None:
        tutor = make_tutor(description="x" * 3000)
        card = format_tutor_card(tutor)
        assert len(card) > TELEGRAM_CAPTION_MAX

    def test_limits_are_telegram_defaults(self) -> None:
        assert TELEGRAM_CAPTION_MAX == 1024
        assert TELEGRAM_MESSAGE_MAX == 4096


@pytest.mark.asyncio
async def test_send_tutor_card_falls_back_when_photo_unavailable() -> None:
    tutor = make_tutor(avatar_file_id="invalid_file_id")
    message = MagicMock()
    message.answer_photo = AsyncMock(
        side_effect=TelegramBadRequest(method=MagicMock(), message="Wrong file identifier")
    )
    message.answer = AsyncMock()

    await send_tutor_card(message, tutor)

    message.answer_photo.assert_awaited_once()
    message.answer.assert_awaited()
    assert "👤" in message.answer.await_args.args[0]
