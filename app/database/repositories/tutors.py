from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import TutorProfile

MODERATION_APPROVED = "approved"
MODERATION_HIDDEN = "hidden"
MODERATION_REJECTED = "rejected"


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
            .where(
                TutorProfile.is_active.is_(True),
                TutorProfile.moderation_status == MODERATION_APPROVED,
            )
            .order_by(TutorProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all_ordered(self, filter_type: str = "all") -> list[TutorProfile]:
        query = (
            select(TutorProfile)
            .options(selectinload(TutorProfile.user))
            .order_by(TutorProfile.created_at.desc())
        )
        if filter_type == "hidden":
            query = query.where(
                TutorProfile.moderation_status.in_([MODERATION_HIDDEN, MODERATION_REJECTED])
            )
        elif filter_type == "recent":
            since = datetime.now(timezone.utc) - timedelta(days=7)
            query = query.where(TutorProfile.created_at >= since)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_moderation_counts(self) -> dict[str, int]:
        total = await self.session.scalar(select(func.count()).select_from(TutorProfile)) or 0
        approved = await self.session.scalar(
            select(func.count())
            .select_from(TutorProfile)
            .where(TutorProfile.moderation_status == MODERATION_APPROVED)
        ) or 0
        hidden = await self.session.scalar(
            select(func.count())
            .select_from(TutorProfile)
            .where(TutorProfile.moderation_status == MODERATION_HIDDEN)
        ) or 0
        rejected = await self.session.scalar(
            select(func.count())
            .select_from(TutorProfile)
            .where(TutorProfile.moderation_status == MODERATION_REJECTED)
        ) or 0
        verified = await self.session.scalar(
            select(func.count())
            .select_from(TutorProfile)
            .where(TutorProfile.is_verified.is_(True))
        ) or 0
        return {
            "total": total,
            "approved": approved,
            "hidden": hidden,
            "rejected": rejected,
            "verified": verified,
        }

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

    async def set_moderation_status(self, profile: TutorProfile, status: str) -> TutorProfile:
        profile.moderation_status = status
        profile.moderated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def toggle_verified(self, profile: TutorProfile) -> TutorProfile:
        profile.is_verified = not profile.is_verified
        profile.verified_at = datetime.now(timezone.utc) if profile.is_verified else None
        profile.moderated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile
