from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TutorContact


class TutorContactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_if_not_exists(self, tutor_id: int, student_telegram_id: int) -> bool:
        result = await self.session.execute(
            select(TutorContact.id).where(
                TutorContact.tutor_id == tutor_id,
                TutorContact.student_telegram_id == student_telegram_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            return False

        self.session.add(
            TutorContact(tutor_id=tutor_id, student_telegram_id=student_telegram_id)
        )
        await self.session.flush()
        return True
