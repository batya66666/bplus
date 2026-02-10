from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Streak


def _day(dt: datetime) -> datetime:
    # normalize to date boundary in UTC
    return dt.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


async def update_streak(session: AsyncSession, user_id: int, now: datetime | None = None) -> Streak:
    now = now or datetime.now(timezone.utc)
    today = _day(now)

    streak = (await session.execute(select(Streak).where(Streak.user_id == user_id))).scalar_one_or_none()
    if not streak:
        streak = Streak(user_id=user_id, current_streak=1, max_streak=1, last_streak_date=today)
        session.add(streak)
        return streak

    last = streak.last_streak_date
    if last is None:
        streak.current_streak = 1
        streak.max_streak = max(streak.max_streak, 1)
        streak.last_streak_date = today
        return streak

    last_day = _day(last)

    if last_day == today:
        # already counted today
        return streak

    if last_day == today - timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1

    streak.max_streak = max(streak.max_streak, streak.current_streak)
    streak.last_streak_date = today
    return streak
