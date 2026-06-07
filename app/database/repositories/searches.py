from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import StudentSearch


class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        exam_keyword: str,
        goal: str,
        current_level: str,
        budget_min: int | None,
        budget_max: int | None,
    ) -> StudentSearch:
        search = StudentSearch(
            user_id=user_id,
            exam_keyword=exam_keyword,
            goal=goal,
            current_level=current_level,
            budget_min=budget_min,
            budget_max=budget_max,
        )
        self.session.add(search)
        await self.session.commit()
        await self.session.refresh(search)
        return search
