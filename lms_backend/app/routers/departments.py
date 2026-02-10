from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_roles
from app.models.core import Department
from app.models.enums import Role
from app.schemas.departments import DepartmentCreate, DepartmentOut

router = APIRouter()


@router.get("", response_model=list[DepartmentOut])
async def list_departments(
    session: AsyncSession = Depends(get_session),
    _=Depends(require_roles(Role.ADMIN.value, Role.MENTOR.value, Role.EMPLOYEE.value, Role.TEAM_LEAD.value, Role.LD_MANAGER.value)),
):
    rows = (await session.execute(select(Department).order_by(Department.name.asc()))).scalars().all()
    return list(rows)


@router.post("", response_model=DepartmentOut, dependencies=[Depends(require_roles(Role.ADMIN.value))])
async def create_department(payload: DepartmentCreate, session: AsyncSession = Depends(get_session)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Department name is empty")

    exists = (await session.execute(select(Department).where(Department.name == name))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Department already exists")

    dep = Department(name=name)
    session.add(dep)
    await session.commit()
    await session.refresh(dep)
    return dep
