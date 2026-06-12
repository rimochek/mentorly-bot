import logging

from sqlalchemy import select

from app.database.models import User
from app.database.repositories.analytics import AdminStats, AnalyticsRepository, PeriodStats
from app.database.session import async_session_factory

logger = logging.getLogger(__name__)

EVENT_START = "start"
EVENT_BUTTON = "button"
EVENT_CALLBACK = "callback"
EVENT_SEARCH = "search"
EVENT_BROWSE = "browse"
EVENT_CONTACT = "contact"
EVENT_TUTOR = "tutor"
EVENT_SUPPORT = "support"


async def track_event(
    telegram_id: int,
    event_type: str,
    event_name: str,
    *,
    user_id: int | None = None,
    properties: dict | None = None,
) -> None:
    try:
        async with async_session_factory() as session:
            resolved_user_id = user_id
            if resolved_user_id is None:
                result = await session.execute(
                    select(User.id).where(User.telegram_id == telegram_id)
                )
                resolved_user_id = result.scalar_one_or_none()

            repo = AnalyticsRepository(session)
            await repo.create_event(
                telegram_id=telegram_id,
                event_type=event_type,
                event_name=event_name,
                user_id=resolved_user_id,
                properties=properties,
            )
    except Exception:
        logger.warning(
            "Failed to track analytics event %s/%s for telegram_id=%s",
            event_type,
            event_name,
            telegram_id,
            exc_info=True,
        )


def _format_period(title: str, stats: PeriodStats) -> str:
    return (
        f"{title}:\n"
        f"• Поисков: {stats.searches}\n"
        f"• Просмотров анкет: {stats.tutor_views}\n"
        f"• Среднее анкет на поиск: {stats.avg_views_per_search}\n"
        f"• Заявок: {stats.applications}\n"
        f"• Регистраций репетиторов: {stats.tutor_registrations}\n"
        f"• Обращений в поддержку: {stats.support_requests}"
    )


def format_admin_stats(stats: AdminStats) -> str:
    lines = [
        "📊 Статистика Mentorly",
        "",
        "Пользователи:",
        f"• Всего: {stats.total_users}",
        f"• Новых сегодня: {stats.new_users_today}",
        f"• Активных сегодня: {stats.active_users_today}",
        f"• С повторными визитами: {stats.returning_users}",
        "",
        _format_period("Сегодня", stats.today),
        "",
        _format_period("За 7 дней", stats.week),
    ]

    if stats.top_buttons:
        lines.extend(["", "Топ кнопок (7 дней):"])
        for index, (name, count) in enumerate(stats.top_buttons, start=1):
            lines.append(f"{index}. {name} — {count}")

    if stats.top_exams:
        lines.extend(["", "Топ экзаменов в поисках (7 дней):"])
        for index, (exam, count) in enumerate(stats.top_exams, start=1):
            lines.append(f"{index}. {exam} — {count}")

    return "\n".join(lines)
