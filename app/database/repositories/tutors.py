from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import TutorProfile


class TutorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: int) -> TutorProfile | None:
        result = await self.session.execute(
            select(TutorProfile)
            .options(selectinload(TutorProfile.user))
            .where(TutorProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, tutor_id: int) -> TutorProfile | None:
        result = await self.session.execute(
            select(TutorProfile)
            .options(selectinload(TutorProfile.user))
            .where(TutorProfile.id == tutor_id)
        )
        return result.scalar_one_or_none()

    async def get_active_tutors(self) -> list[TutorProfile]:
        result = await self.session.execute(
            select(TutorProfile)
            .options(selectinload(TutorProfile.user))
            .where(TutorProfile.is_active.is_(True))
            .order_by(TutorProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        user_id: int,
        name: str,
        age: int,
        city: str,
        place_of_study: str,
        price_min: int,
        price_max: int,
        description: str,
        avatar_file_id: str | None = None,
    ) -> TutorProfile:
        profile = TutorProfile(
            user_id=user_id,
            name=name,
            age=age,
            city=city,
            place_of_study=place_of_study,
            price_min=price_min,
            price_max=price_max,
            description=description,
            avatar_file_id=avatar_file_id,
        )
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update_field(self, profile: TutorProfile, field: str, value: object) -> TutorProfile:
        setattr(profile, field, value)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def toggle_active(self, profile: TutorProfile) -> TutorProfile:
        profile.is_active = not profile.is_active
        await self.session.commit()
        await self.session.refresh(profile)
        return profile
