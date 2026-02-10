from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.core import User
from app.schemas.auth import LoginIn, TokenOut
from app.security.passwords import verify_password
from app.security.jwt import create_access_token
from app.settings import settings
from app.services.streaks import update_streak

router = APIRouter()


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, session: AsyncSession = Depends(get_session)) -> TokenOut:
    user = (await session.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")

    now = datetime.now(timezone.utc)

    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=429, detail="Вход временно заблокирован. Попробуйте позже.")

    ok = verify_password(data.password, user.password_hash)

    if not ok:
        user.failed_login_count += 1
        if user.failed_login_count >= settings.login_max_attempts:
            user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
            user.failed_login_count = 0
        await session.commit()
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")

    # success
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now

    await update_streak(session, user.id, now=now)

    await session.commit()

    token = create_access_token(sub=str(user.id))
    return TokenOut(access_token=token)
