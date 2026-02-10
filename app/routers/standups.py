from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.core import DailyReportRevision
from app.db import get_session
from app.deps import get_current_user, require_roles
from app.models.core import DailyReport, User
from app.models.enums import Role, ReportStatus
from app.schemas.standups import ReportCreate, ReportUpdate, ReportOut, MentorDecisionIn

router = APIRouter()


@router.post("", response_model=ReportOut)
async def create_report(payload: ReportCreate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    text_done = payload.text_done.strip()
    text_plan = payload.text_plan.strip()
    text_blockers = payload.text_blockers.strip()

    if not (text_done and text_plan and text_blockers):
        raise HTTPException(status_code=400, detail="Пустой отчет отправить нельзя")

    r = DailyReport(
        user_id=user.id,
        day_number=payload.day_number,
        text_done=text_done,
        text_plan=text_plan,
        text_blockers=text_blockers,
        status=ReportStatus.PENDING.value,
    )
    session.add(r)
    await session.flush()  # получаем r.id без commit

    session.add(DailyReportRevision(
        report_id=r.id,
        text_done=r.text_done,
        text_plan=r.text_plan,
        text_blockers=r.text_blockers,
        status=r.status,
        mentor_comment=r.mentor_comment,
    ))

    await session.commit()
    await session.refresh(r)
    return r



@router.get("/my", response_model=list[ReportOut])
async def my_reports(session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    rows = (await session.execute(select(DailyReport).where(DailyReport.user_id == user.id).order_by(DailyReport.id.desc()))).scalars().all()
    return list(rows)

@router.get(
    "/mentor",
    dependencies=[Depends(require_roles(Role.MENTOR.value, Role.TEAM_LEAD.value, Role.ADMIN.value))],
)
async def mentor_reports(
    session: AsyncSession = Depends(get_session),
    me=Depends(get_current_user),
):
    """
    MVP: ментор видит отчёты пользователей из своего отдела.
    """
    if me.department_id is None:
        return []

    # берём людей отдела (кроме самого ментора)
    user_rows = (
        await session.execute(
            select(User.id, User.full_name, User.email)
            .where(User.department_id == me.department_id)
            .where(User.id != me.id)
        )
    ).all()
    user_map = {u.id: {"full_name": u.full_name, "email": u.email} for u in user_rows}

    if not user_map:
        return []

    reports = (
        await session.execute(
            select(DailyReport)
            .where(DailyReport.user_id.in_(list(user_map.keys())))
            .order_by(DailyReport.id.desc())
        )
    ).scalars().all()

    # возвращаем расширенный объект, не response_model, чтобы не ломать текущие схемы
    out = []
    for r in reports:
        u = user_map.get(r.user_id, {"full_name": "Unknown", "email": ""})
        out.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_full_name": u["full_name"],
            "user_email": u["email"],
            "day_number": r.day_number,
            "text_done": r.text_done,
            "text_plan": r.text_plan,
            "text_blockers": r.text_blockers,
            "status": r.status,
            "mentor_comment": r.mentor_comment,
        })
    return out
@router.get("/{report_id}/history")
async def report_history(
    report_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    report = (await session.execute(select(DailyReport).where(DailyReport.id == report_id))).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # сотрудник видит только своё, ментор/тимлид/админ — можно расширить потом
    if report.user_id != user.id and user.role not in [Role.MENTOR.value, Role.TEAM_LEAD.value, Role.ADMIN.value]:
        raise HTTPException(status_code=403, detail="Forbidden")

    rows = (
        await session.execute(
            select(DailyReportRevision)
            .where(DailyReportRevision.report_id == report_id)
            .order_by(DailyReportRevision.id.desc())
        )
    ).scalars().all()

    return [{
        "id": r.id,
        "created_at": r.created_at,
        "status": r.status,
        "mentor_comment": r.mentor_comment,
        "text_done": r.text_done,
        "text_plan": r.text_plan,
        "text_blockers": r.text_blockers,
    } for r in rows]
@router.put("/{report_id}", response_model=ReportOut)
async def update_report(
    report_id: int,
    payload: ReportUpdate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    report = (await session.execute(select(DailyReport).where(DailyReport.id == report_id))).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # можно редактировать только если на доработке
    if report.status != ReportStatus.REVISION.value:
        raise HTTPException(status_code=400, detail="Редактировать можно только отчёт со статусом REVISION")

    text_done = payload.text_done.strip()
    text_plan = payload.text_plan.strip()
    text_blockers = payload.text_blockers.strip()
    if not (text_done and text_plan and text_blockers):
        raise HTTPException(status_code=400, detail="Пустой отчет отправить нельзя")

    # обновляем отчёт: заново на проверку
    report.text_done = text_done
    report.text_plan = text_plan
    report.text_blockers = text_blockers
    report.status = ReportStatus.PENDING.value
    report.mentor_comment = None

    # сохраняем ревизию после изменения
    session.add(DailyReportRevision(
        report_id=report.id,
        text_done=report.text_done,
        text_plan=report.text_plan,
        text_blockers=report.text_blockers,
        status=report.status,
        mentor_comment=report.mentor_comment,
    ))

    await session.commit()
    await session.refresh(report)
    return report



@router.post(
    "/{report_id}/mentor_decision",
    response_model=ReportOut,
    dependencies=[Depends(require_roles(Role.MENTOR.value, Role.TEAM_LEAD.value, Role.ADMIN.value))],
)
async def mentor_decision(
    report_id: int,
    payload: MentorDecisionIn,
    session: AsyncSession = Depends(get_session),
):
    report = (await session.execute(
        select(DailyReport).where(DailyReport.id == report_id)
    )).scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # применяем решение ментора
    if payload.action == ReportStatus.REVISION.value:
        if not payload.mentor_comment or not payload.mentor_comment.strip():
            raise HTTPException(status_code=400, detail="Комментарий обязателен при возврате на доработку")
        report.status = ReportStatus.REVISION.value
        report.mentor_comment = payload.mentor_comment.strip()
    else:
        report.status = ReportStatus.ACCEPTED.value
        report.mentor_comment = payload.mentor_comment.strip() if payload.mentor_comment else None

    # сохраняем снимок (ревизию)
    rev = DailyReportRevision(
        report_id=report.id,
        text_done=report.text_done,
        text_plan=report.text_plan,
        text_blockers=report.text_blockers,
        status=report.status,
        mentor_comment=report.mentor_comment,
    )
    session.add(rev)

    await session.commit()
    await session.refresh(report)
    return report

