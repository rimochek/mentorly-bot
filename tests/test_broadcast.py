import pytest

from app.database.repositories.users import UserRepository


@pytest.mark.asyncio
async def test_get_telegram_ids_tutors(session):
    user_repo = UserRepository(session)
    ids = await user_repo.get_telegram_ids_by_audience("tutors")
    assert 200001 in ids
    assert 100001 not in ids


@pytest.mark.asyncio
async def test_get_telegram_ids_students(session):
    user_repo = UserRepository(session)
    ids = await user_repo.get_telegram_ids_by_audience("students")
    assert 100001 in ids
    assert 200001 not in ids


@pytest.mark.asyncio
async def test_get_telegram_ids_all(session):
    user_repo = UserRepository(session)
    ids = await user_repo.get_telegram_ids_by_audience("all")
    assert len(ids) >= 2
