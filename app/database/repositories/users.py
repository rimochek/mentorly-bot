from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.tutor_profile))
            .where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.username = username
            user.full_name = full_name
            await self.session.commit()
            await self.session.refresh(user)
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user, True

    async def record_visit(self, user: User) -> User:
        now = datetime.now(timezone.utc)
        user.last_seen_at = now
        user.visit_count = (user.visit_count or 0) + 1
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def set_role(self, user: User, role: str) -> User:
        user.role = role
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.tutor_profile))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_telegram_ids_by_audience(self, audience: str) -> list[int]:
        query = select(User.telegram_id)
        if audience == "tutors":
            query = query.where(User.role == "tutor")
        elif audience == "students":
            query = query.where(or_(User.role.is_(None), User.role != "tutor"))
        result = await self.session.execute(query)
        return list(result.scalars().all())
