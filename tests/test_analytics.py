from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, Message, User as TgUser
from sqlalchemy import select

from app.bot.filters.admin import AdminFilter
from app.bot.middlewares.analytics import KNOWN_BUTTONS, _is_trackable_callback
from app.database.models import AnalyticsEvent, User
from app.database.repositories.analytics import AdminStats, AnalyticsRepository, PeriodStats
from app.database.repositories.users import UserRepository
from app.services.analytics import format_admin_stats, track_event


@pytest.mark.asyncio
async def test_create_event(session):
    repo = AnalyticsRepository(session)
    user = await session.scalar(select(User).where(User.telegram_id == 100001))

    event = await repo.create_event(
        telegram_id=100001,
        event_type="button",
        event_name="🔎 Найти репетитора",
        user_id=user.id,
    )

    assert event.id is not None
    assert event.event_name == "🔎 Найти репетитора"
    assert event.user_id == user.id


@pytest.mark.asyncio
async def test_record_visit(session):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(100001)

    await user_repo.record_visit(user)
    await session.refresh(user)

    assert user.visit_count == 1
    assert user.last_seen_at is not None

    await user_repo.record_visit(user)
    await session.refresh(user)
    assert user.visit_count == 2


@pytest.mark.asyncio
async def test_get_admin_stats_aggregates(session):
    repo = AnalyticsRepository(session)
    user = await session.scalar(select(User).where(User.telegram_id == 100001))
    now = datetime.now(timezone.utc)

    events = [
        AnalyticsEvent(
            telegram_id=100001,
            user_id=user.id,
            event_type="search",
            event_name="search_completed",
            properties={"exam": "IELTS"},
            created_at=now,
        ),
        AnalyticsEvent(
            telegram_id=100001,
            user_id=user.id,
            event_type="search",
            event_name="search_completed",
            properties={"exam": "IELTS"},
            created_at=now,
        ),
        AnalyticsEvent(
            telegram_id=100001,
            user_id=user.id,
            event_type="browse",
            event_name="tutor_viewed",
            created_at=now,
        ),
        AnalyticsEvent(
            telegram_id=100001,
            user_id=user.id,
            event_type="browse",
            event_name="tutor_viewed",
            created_at=now,
        ),
        AnalyticsEvent(
            telegram_id=100001,
            user_id=user.id,
            event_type="browse",
            event_name="tutor_viewed",
            created_at=now,
        ),
        AnalyticsEvent(
            telegram_id=100001,
            user_id=user.id,
            event_type="contact",
            event_name="application_sent",
            created_at=now,
        ),
        AnalyticsEvent(
            telegram_id=100001,
            user_id=user.id,
            event_type="button",
            event_name="🔎 Найти репетитора",
            created_at=now,
        ),
        AnalyticsEvent(
            telegram_id=100001,
            user_id=user.id,
            event_type="button",
            event_name="🔎 Найти репетитора",
            created_at=now - timedelta(days=10),
        ),
    ]
    session.add_all(events)
    await session.commit()

    stats = await repo.get_admin_stats()

    assert stats.total_users >= 2
    assert stats.today.searches == 2
    assert stats.today.tutor_views == 3
    assert stats.today.avg_views_per_search == 1.5
    assert stats.today.applications == 1
    assert stats.top_buttons[0] == ("🔎 Найти репетитора", 1)
    assert stats.top_exams[0] == ("IELTS", 2)


def test_format_admin_stats():
    stats = AdminStats(
        total_users=10,
        new_users_today=2,
        active_users_today=5,
        returning_users=3,
        today=PeriodStats(searches=4, tutor_views=8, avg_views_per_search=2.0, applications=1),
        week=PeriodStats(searches=20, tutor_views=40, avg_views_per_search=2.0, applications=5),
        top_buttons=[("🔎 Найти репетитора", 15)],
        top_exams=[("IELTS", 7)],
    )

    text = format_admin_stats(stats)

    assert "📊 Статистика Mentorly" in text
    assert "Всего: 10" in text
    assert "Поисков: 4" in text
    assert "Среднее анкет на поиск: 2.0" in text
    assert "🔎 Найти репетитора — 15" in text
    assert "IELTS — 7" in text


@pytest.mark.asyncio
async def test_admin_filter():
    admin_filter = AdminFilter()
    admin_message = Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=Chat(id=1, type="private"),
        from_user=TgUser(id=999, is_bot=False, first_name="Admin"),
    )
    user_message = Message(
        message_id=2,
        date=datetime.now(timezone.utc),
        chat=Chat(id=2, type="private"),
        from_user=TgUser(id=111, is_bot=False, first_name="User"),
    )

    settings = MagicMock()
    settings.admin_id_list = [999]

    with patch("app.bot.filters.admin.get_settings", return_value=settings):
        assert await admin_filter(admin_message) is True
        assert await admin_filter(user_message) is False


def test_known_buttons_include_main_menu():
    assert "🔎 Найти репетитора" in KNOWN_BUTTONS
    assert "➡️ Следующий репетитор" in KNOWN_BUTTONS


def test_trackable_callbacks():
    assert _is_trackable_callback("next_tutor")
    assert _is_trackable_callback("contact:42")
    assert _is_trackable_callback("edit:name")
    assert not _is_trackable_callback("unknown")


@pytest.mark.asyncio
async def test_track_event_uses_repository():
    mock_repo = AsyncMock()
    mock_repo.create_event = AsyncMock()
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 7
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.analytics.async_session_factory", return_value=mock_session):
        with patch("app.services.analytics.AnalyticsRepository", return_value=mock_repo):
            await track_event(100001, "start", "bot_start", properties={"is_new_user": True})

    mock_repo.create_event.assert_awaited_once()
    call_kwargs = mock_repo.create_event.await_args.kwargs
    assert call_kwargs["telegram_id"] == 100001
    assert call_kwargs["event_type"] == "start"
    assert call_kwargs["user_id"] == 7
