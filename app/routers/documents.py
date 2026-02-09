from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models.core import Document
from app.schemas.documents import DocumentOut

router = APIRouter()


@router.get("", response_model=list[DocumentOut])
async def list_documents(q: str | None = None, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    stmt = select(Document).order_by(Document.id.desc())
    if q:
        stmt = stmt.where(Document.title.ilike(f"%{q}%"))
    rows = (await session.execute(stmt)).scalars().all()
    # MVP: access_level проверим позже (All/Admins Only + отделы)
    return list(rows)
