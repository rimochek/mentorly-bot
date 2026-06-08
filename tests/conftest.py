from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, TutorProfile, User


def make_tutor(**kwargs) -> TutorProfile:
    defaults: dict = {
        "id": 1,
        "user_id": 1,
        "name": "Test Tutor",
        "age": 22,
        "city": "Almaty",
        "place_of_study": "NU",
        "price_min": 4000,
        "price_max": 6000,
        "description": "Готовлю к IELTS. IELTS 8.0.",
        "avatar_file_id": None,
        "is_active": True,
        "views_count": 0,
        "contacts_count": 0,
        "last_shown_at": None,
        "shown_today_count": 0,
        "last_stats_reset_at": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return TutorProfile(**defaults)


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db_session:
        user = User(telegram_id=100001, username="student", full_name="Student")
        db_session.add(user)
        await db_session.flush()

        tutor_user = User(telegram_id=200001, username="tutor", full_name="Tutor", role="tutor")
        db_session.add(tutor_user)
        await db_session.flush()

        tutor = TutorProfile(
            user_id=tutor_user.id,
            name="IELTS Tutor",
            age=23,
            city="Almaty",
            place_of_study="NU",
            price_min=4000,
            price_max=6000,
            description="Готовлю к IELTS",
        )
        db_session.add(tutor)
        await db_session.commit()
        await db_session.refresh(tutor)

        yield db_session

    await engine.dispose()
