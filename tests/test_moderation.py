from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User as TgUser

from app.bot.filters.admin import AdminFilter
from app.database.repositories.tutors import (
    MODERATION_APPROVED,
    MODERATION_HIDDEN,
    TutorRepository,
)
from app.services.tutor_card import format_moderation_status, format_tutor_header

from tests.conftest import make_tutor


def test_verified_badge_in_header() -> None:
    tutor = make_tutor(is_verified=True)
    header = format_tutor_header(tutor)
    assert "Verified Mentor" in header

    tutor_plain = make_tutor(is_verified=False)
    header_plain = format_tutor_header(tutor_plain)
    assert "Verified Mentor" not in header_plain


def test_moderation_status_labels() -> None:
    assert format_moderation_status(make_tutor(moderation_status=MODERATION_HIDDEN)) is not None
    assert format_moderation_status(make_tutor(moderation_status=MODERATION_APPROVED)) is None


@pytest.mark.asyncio
async def test_set_moderation_status(session):
    tutor_repo = TutorRepository(session)
    tutor = await tutor_repo.get_by_id(1)

    updated = await tutor_repo.set_moderation_status(tutor, MODERATION_HIDDEN)
    assert updated.moderation_status == MODERATION_HIDDEN
    assert updated.moderated_at is not None


@pytest.mark.asyncio
async def test_toggle_verified(session):
    tutor_repo = TutorRepository(session)
    tutor = await tutor_repo.get_by_id(1)
    assert tutor.is_verified is False

    verified = await tutor_repo.toggle_verified(tutor)
    assert verified.is_verified is True
    assert verified.verified_at is not None

    unverified = await tutor_repo.toggle_verified(verified)
    assert unverified.is_verified is False
    assert unverified.verified_at is None


@pytest.mark.asyncio
async def test_get_active_tutors_excludes_hidden(session):
    tutor_repo = TutorRepository(session)
    tutor = await tutor_repo.get_by_id(1)
    await tutor_repo.set_moderation_status(tutor, MODERATION_HIDDEN)

    active = await tutor_repo.get_active_tutors()
    assert all(t.moderation_status == MODERATION_APPROVED for t in active)
    assert all(t.id != tutor.id for t in active)


@pytest.mark.asyncio
async def test_admin_filter_callback():
    admin_filter = AdminFilter()
    callback = CallbackQuery(
        id="1",
        from_user=TgUser(id=999, is_bot=False, first_name="Admin"),
        chat_instance="1",
        message=Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=Chat(id=1, type="private"),
        ),
    )
    settings = MagicMock()
    settings.admin_id_list = [999]

    with patch("app.bot.filters.admin.get_settings", return_value=settings):
        assert await admin_filter(callback) is True


@pytest.mark.asyncio
async def test_moderation_counts(session):
    tutor_repo = TutorRepository(session)
    counts = await tutor_repo.get_moderation_counts()
    assert counts["total"] >= 1
    assert "verified" in counts
