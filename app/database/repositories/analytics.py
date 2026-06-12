from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AnalyticsEvent, User


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _start_of_today_utc() -> datetime:
    now = _utc_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass
class PeriodStats:
    searches: int = 0
    tutor_views: int = 0
    avg_views_per_search: float = 0.0
    applications: int = 0
    tutor_registrations: int = 0
    support_requests: int = 0


@dataclass
class AdminStats:
    total_users: int = 0
    new_users_today: int = 0
    active_users_today: int = 0
    returning_users: int = 0
    today: PeriodStats = field(default_factory=PeriodStats)
    week: PeriodStats = field(default_factory=PeriodStats)
    top_buttons: list[tuple[str, int]] = field(default_factory=list)
    top_exams: list[tuple[str, int]] = field(default_factory=list)


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_event(
        self,
        telegram_id: int,
        event_type: str,
        event_name: str,
        *,
        user_id: int | None = None,
        properties: dict | None = None,
    ) -> AnalyticsEvent:
        event = AnalyticsEvent(
            telegram_id=telegram_id,
            user_id=user_id,
            event_type=event_type,
            event_name=event_name,
            properties=properties,
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def _count_events(
        self,
        since: datetime,
        event_type: str,
        event_name: str | None = None,
        event_names: list[str] | None = None,
    ) -> int:
        query = select(func.count()).select_from(AnalyticsEvent).where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.event_type == event_type,
        )
        if event_name is not None:
            query = query.where(AnalyticsEvent.event_name == event_name)
        if event_names is not None:
            query = query.where(AnalyticsEvent.event_name.in_(event_names))
        result = await self.session.execute(query)
        return result.scalar_one()

    async def _period_stats(self, since: datetime) -> PeriodStats:
        searches = await self._count_events(
            since,
            "search",
            event_names=["search_completed", "search_no_match"],
        )
        search_completed = await self._count_events(since, "search", event_name="search_completed")
        tutor_views = await self._count_events(since, "browse", event_name="tutor_viewed")
        applications = await self._count_events(since, "contact", event_name="application_sent")
        tutor_registrations = await self._count_events(since, "tutor", event_name="profile_created")
        support_requests = await self._count_events(since, "support", event_name="complaint_submitted")

        avg_views = round(tutor_views / search_completed, 1) if search_completed else 0.0

        return PeriodStats(
            searches=searches,
            tutor_views=tutor_views,
            avg_views_per_search=avg_views,
            applications=applications,
            tutor_registrations=tutor_registrations,
            support_requests=support_requests,
        )

    async def get_admin_stats(self) -> AdminStats:
        today_start = _start_of_today_utc()
        week_start = _utc_now() - timedelta(days=7)

        total_users = await self.session.scalar(select(func.count()).select_from(User)) or 0
        new_users_today = await self.session.scalar(
            select(func.count()).select_from(User).where(User.created_at >= today_start)
        ) or 0
        returning_users = await self.session.scalar(
            select(func.count()).select_from(User).where(User.visit_count > 1)
        ) or 0
        active_users_today = await self.session.scalar(
            select(func.count(func.distinct(AnalyticsEvent.telegram_id)))
            .select_from(AnalyticsEvent)
            .where(AnalyticsEvent.created_at >= today_start)
        ) or 0

        top_buttons_result = await self.session.execute(
            select(AnalyticsEvent.event_name, func.count().label("cnt"))
            .where(
                AnalyticsEvent.created_at >= week_start,
                AnalyticsEvent.event_type.in_(["button", "callback"]),
            )
            .group_by(AnalyticsEvent.event_name)
            .order_by(func.count().desc())
            .limit(5)
        )
        top_buttons = [(row.event_name, row.cnt) for row in top_buttons_result]

        exam_key = cast(AnalyticsEvent.properties["exam"], String)
        top_exams_result = await self.session.execute(
            select(exam_key.label("exam"), func.count().label("cnt"))
            .where(
                AnalyticsEvent.created_at >= week_start,
                AnalyticsEvent.event_type == "search",
                AnalyticsEvent.event_name.in_(["search_completed", "search_no_match"]),
                AnalyticsEvent.properties.isnot(None),
            )
            .group_by(exam_key)
            .order_by(func.count().desc())
            .limit(5)
        )
        top_exams = [
            (str(row.exam).strip('"'), row.cnt)
            for row in top_exams_result
            if row.exam
        ]

        return AdminStats(
            total_users=total_users,
            new_users_today=new_users_today,
            active_users_today=active_users_today,
            returning_users=returning_users,
            today=await self._period_stats(today_start),
            week=await self._period_stats(week_start),
            top_buttons=top_buttons,
            top_exams=top_exams,
        )
