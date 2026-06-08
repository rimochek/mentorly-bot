import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.tutor_contacts import TutorContactRepository
from app.database.repositories.tutors import TutorRepository

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_same_day(dt: datetime | None, today: datetime) -> bool:
    if dt is None:
        return False
    return dt.date() == today.date()


async def increment_tutor_view(session: AsyncSession, tutor_id: int) -> None:
    repo = TutorRepository(session)
    tutor = await repo.get_by_id(tutor_id)
    if not tutor:
        logger.warning("View increment skipped: tutor %s not found", tutor_id)
        return

    now = _now()
    if not _is_same_day(tutor.last_stats_reset_at, now):
        tutor.shown_today_count = 0
        tutor.last_stats_reset_at = now

    tutor.views_count += 1
    tutor.shown_today_count += 1
    tutor.last_shown_at = now
    await session.commit()

    logger.info(
        "Tutor view recorded: tutor_id=%s views_count=%s shown_today=%s",
        tutor_id,
        tutor.views_count,
        tutor.shown_today_count,
    )


async def increment_tutor_contact(
    session: AsyncSession,
    tutor_id: int,
    student_telegram_id: int,
) -> bool:
    repo = TutorRepository(session)
    tutor = await repo.get_by_id(tutor_id)
    if not tutor:
        logger.warning("Contact increment skipped: tutor %s not found", tutor_id)
        return False

    contact_repo = TutorContactRepository(session)
    created = await contact_repo.create_if_not_exists(tutor_id, student_telegram_id)
    if not created:
        logger.info(
            "Contact not counted (duplicate): tutor_id=%s student_telegram_id=%s",
            tutor_id,
            student_telegram_id,
        )
        return False

    tutor.contacts_count += 1
    await session.commit()

    logger.info(
        "Tutor contact recorded: tutor_id=%s student_telegram_id=%s contacts_count=%s",
        tutor_id,
        student_telegram_id,
        tutor.contacts_count,
    )
    return True


def format_tutor_stats(tutor) -> str:
    views = tutor.views_count
    contacts = tutor.contacts_count
    conversion = round(contacts / views * 100) if views > 0 else 0

    if tutor.last_shown_at:
        last_shown = tutor.last_shown_at.strftime("%d.%m.%Y %H:%M")
    else:
        last_shown = "—"

    return (
        "📊 Ваша статистика\n\n"
        f"👀 Показы анкеты: {views}\n"
        f'📩 Нажатий "Связаться": {contacts}\n'
        f"📈 Конверсия: {conversion}%\n\n"
        f"Последний показ: {last_shown}"
    )
