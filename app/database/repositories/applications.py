from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.database.models import Application, TutorProfile


class ApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        student_id: int,
        tutor_id: int,
        exam_keyword: str,
        goal: str,
        current_level: str,
        budget_text: str,
    ) -> Application:
        application = Application(
            student_id=student_id,
            tutor_id=tutor_id,
            exam_keyword=exam_keyword,
            goal=goal,
            current_level=current_level,
            budget_text=budget_text,
        )
        self.session.add(application)
        await self.session.commit()
        await self.session.refresh(application)
        return application

    async def get_with_relations(self, application_id: int) -> Application | None:
        result = await self.session.execute(
            select(Application)
            .options(
                selectinload(Application.student),
                selectinload(Application.tutor).selectinload(TutorProfile.user),
            )
            .where(Application.id == application_id)
        )
        return result.scalar_one_or_none()
