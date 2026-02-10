from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_roles
from app.models.core import User, Department
from app.schemas.users import UserCreate, UserOut
from app.schemas.admin import UserUpdate, ResetPasswordIn
from app.security.passwords import hash_password
from app.models.enums import Role

router = APIRouter()


@router.post("", response_model=UserOut, dependencies=[Depends(require_roles(Role.ADMIN.value))])
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_session)) -> UserOut:
    exists = (await session.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Email already exists")

    if payload.department_id is not None:
        dep = (await session.execute(select(Department).where(Department.id == payload.department_id))).scalar_one_or_none()
        if not dep:
            raise HTTPException(status_code=400, detail="Department not found")

    u = User(
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role.value,
        department_id=payload.department_id,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@router.get("", response_model=list[UserOut], dependencies=[Depends(require_roles(Role.ADMIN.value))])
async def list_users(session: AsyncSession = Depends(get_session)) -> list[UserOut]:
    rows = (await session.execute(select(User).order_by(User.id.asc()))).scalars().all()
    return list(rows)


@router.patch("/{user_id}", response_model=UserOut, dependencies=[Depends(require_roles(Role.ADMIN.value))])
async def update_user(user_id: int, payload: UserUpdate, session: AsyncSession = Depends(get_session)) -> UserOut:
    u = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        u.full_name = payload.full_name.strip()

    if payload.role is not None:
        u.role = payload.role.value

    if payload.department_id is not None:
        dep = (await session.execute(select(Department).where(Department.id == payload.department_id))).scalar_one_or_none()
        if not dep:
            raise HTTPException(status_code=400, detail="Department not found")
        u.department_id = payload.department_id

    if payload.is_active is not None:
        u.is_active = bool(payload.is_active)

    await session.commit()
    await session.refresh(u)
    return u


@router.post("/{user_id}/reset_password", dependencies=[Depends(require_roles(Role.ADMIN.value))])
async def reset_password(user_id: int, payload: ResetPasswordIn, session: AsyncSession = Depends(get_session)):
    u = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.password_hash = hash_password(payload.new_password)
    await session.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user=Depends(require_roles(Role.ADMIN.value, Role.MENTOR.value, Role.EMPLOYEE.value, Role.TEAM_LEAD.value, Role.LD_MANAGER.value))):
    return user
