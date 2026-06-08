from sqlalchemy import select

from app.database.models import TutorContact, TutorProfile
from app.services.tutor_stats import format_tutor_stats, increment_tutor_contact, increment_tutor_view

from tests.conftest import make_tutor


class TestFormatTutorStats:
    def test_zero_views_shows_zero_conversion(self) -> None:
        tutor = make_tutor(views_count=0, contacts_count=0)
        text = format_tutor_stats(tutor)
        assert "Показы анкеты: 0" in text
        assert "Конверсия: 0%" in text

    def test_conversion_calculation(self) -> None:
        tutor = make_tutor(views_count=10, contacts_count=3)
        text = format_tutor_stats(tutor)
        assert "Конверсия: 30%" in text
        assert 'Нажатий "Связаться": 3' in text

    def test_last_shown_dash_when_never_shown(self) -> None:
        tutor = make_tutor(last_shown_at=None)
        text = format_tutor_stats(tutor)
        assert "Последний показ: —" in text


async def test_increment_tutor_view(session) -> None:
    result = await session.execute(select(TutorProfile))
    tutor = result.scalar_one()
    tutor_id = tutor.id

    await increment_tutor_view(session, tutor_id)

    await session.refresh(tutor)
    assert tutor.views_count == 1
    assert tutor.shown_today_count == 1
    assert tutor.last_shown_at is not None


async def test_increment_tutor_contact_dedup(session) -> None:
    result = await session.execute(select(TutorProfile))
    tutor = result.scalar_one()
    tutor_id = tutor.id
    student_telegram_id = 100001

    first = await increment_tutor_contact(session, tutor_id, student_telegram_id)
    await session.refresh(tutor)
    assert first is True
    assert tutor.contacts_count == 1

    second = await increment_tutor_contact(session, tutor_id, student_telegram_id)
    await session.refresh(tutor)
    assert second is False
    assert tutor.contacts_count == 1

    contacts = await session.execute(select(TutorContact))
    assert len(contacts.scalars().all()) == 1
