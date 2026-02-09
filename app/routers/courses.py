from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user, require_roles

from app.models.core import Course, Enrollment, Lesson, VideoProgress, User
from app.models.enums import Role, EnrollmentStatus

from app.schemas.courses import CourseOut, EnrollmentOut, VideoProgressIn, CourseCatalogOut

router = APIRouter()




@router.get("", response_model=list[CourseOut])
async def list_courses(session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    # MVP: показываем все курсы; дальше добавим доступ по отделам/назначениям.
    rows = (await session.execute(select(Course).order_by(Course.id.desc()))).scalars().all()
    return list(rows)


@router.get("/my", response_model=list[EnrollmentOut])
async def my_enrollments(session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    rows = (await session.execute(select(Enrollment).where(Enrollment.user_id == user.id))).scalars().all()
    return list(rows)
    
@router.get("/my_full")
async def my_courses_full(session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    enrolls = (
        await session.execute(
            select(Enrollment).where(Enrollment.user_id == user.id)
        )
    ).scalars().all()

    if not enrolls:
        return []

    course_ids = [e.course_id for e in enrolls]

    courses = (
        await session.execute(
            select(Course).where(Course.id.in_(course_ids))
        )
    ).scalars().all()
    course_map = {c.id: c for c in courses}

    lessons = (
        await session.execute(
            select(Lesson)
            .where(Lesson.course_id.in_(course_ids))
            .order_by(Lesson.course_id.asc(), Lesson.order.asc())
        )
    ).scalars().all()

    # прогресс видео для пользователя
    vp_rows = (
        await session.execute(
            select(VideoProgress).where(VideoProgress.user_id == user.id)
        )
    ).scalars().all()
    vp_map = {vp.lesson_id: vp for vp in vp_rows}

    # группируем уроки по курсу
    by_course = {}
    for l in lessons:
        by_course.setdefault(l.course_id, []).append(l)

    result = []
    for e in enrolls:
        c = course_map.get(e.course_id)
        if not c:
            continue

        ls_list = by_course.get(c.id, [])
        lessons_out = []

        completed_cnt = 0
        for l in ls_list:
            vp = vp_map.get(l.id)
            watched = int(vp.watched_percent) if vp else 0
            pos = int(vp.position_sec) if vp else 0
            is_completed = watched >= 100
            if is_completed:
                completed_cnt += 1

            lessons_out.append({
                "id": l.id,
                "order": l.order,
                "title": l.title,
                "video_url": l.video_url,
                "watched_percent": watched,
                "position_sec": pos,
                "is_completed": is_completed,
            })

        total = len(ls_list)
        progress = int((completed_cnt / total) * 100) if total else 0

        # синхронизируем enrollment.progress_percent
        if e.progress_percent != progress:
            e.progress_percent = progress

            if progress >= 100:
                e.status = EnrollmentStatus.COMPLETED.value
            elif progress > 0 and e.status == EnrollmentStatus.ASSIGNED.value:
                e.status = EnrollmentStatus.IN_PROGRESS.value

        result.append({
            "course_id": c.id,
            "title": c.title,
            "description": c.description,
            "is_mandatory": c.is_mandatory,
            "status": e.status,
            "progress_percent": e.progress_percent,
            "deadline_at": e.deadline_at,
            "lessons": lessons_out,
        })

    await session.commit()
    return result

@router.get("/catalog", response_model=list[CourseCatalogOut])
async def catalog(
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    enrolls = (
        await session.execute(select(Enrollment).where(Enrollment.user_id == user.id))
    ).scalars().all()
    enr_map = {e.course_id: e for e in enrolls}

    if user.role == Role.ADMIN.value:
        courses = (await session.execute(select(Course).order_by(Course.id.desc()))).scalars().all()
    else:
        assigned_ids = list(enr_map.keys())
        cond = Course.is_public.is_(True)
        if assigned_ids:
            cond = or_(Course.is_public.is_(True), Course.id.in_(assigned_ids))
        courses = (await session.execute(select(Course).where(cond).order_by(Course.id.desc()))).scalars().all()

    out: list[CourseCatalogOut] = []
    for c in courses:
        e = enr_map.get(c.id)
        out.append(CourseCatalogOut(
            id=c.id,
            title=c.title,
            description=c.description,
            is_mandatory=c.is_mandatory,
            deadline_days=c.deadline_days,
            is_public=c.is_public,
            enrolled=e is not None,
            status=e.status if e else None,
            progress_percent=e.progress_percent if e else None,
            deadline_at=e.deadline_at if e else None,
        ))
    return out

@router.get("/{course_id}/lessons")
async def list_lessons(course_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    lessons = (await session.execute(select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.order))).scalars().all()
    return [{"id": l.id, "order": l.order, "title": l.title, "video_url": l.video_url} for l in lessons]

from sqlalchemy import select, or_

@router.post("/{course_id}/start")
async def start_course(
    course_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    course = (await session.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enr = (
        await session.execute(
            select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        )
    ).scalar_one_or_none()

    if enr:
        if enr.status == EnrollmentStatus.ASSIGNED.value:
            enr.status = EnrollmentStatus.IN_PROGRESS.value
            await session.commit()
        return {"ok": True, "already_enrolled": True}

    if not course.is_public:
        raise HTTPException(status_code=403, detail="Course is not available without assignment")

    deadline_at = None
    if course.deadline_days and course.deadline_days > 0:
        deadline_at = datetime.now(timezone.utc) + timedelta(days=course.deadline_days)

    session.add(Enrollment(
        user_id=user.id,
        course_id=course_id,
        status=EnrollmentStatus.IN_PROGRESS.value,
        progress_percent=0,
        deadline_at=deadline_at,
    ))
    await session.commit()
    return {"ok": True, "already_enrolled": False}

@router.get("/catalog", response_model=list[CourseCatalogOut])
async def catalog(
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    enrolls = (
        await session.execute(select(Enrollment).where(Enrollment.user_id == user.id))
    ).scalars().all()
    enr_map = {e.course_id: e for e in enrolls}

    # админ видит всё, остальные: public + назначенные
    if user.role == Role.ADMIN.value:
        courses = (await session.execute(select(Course).order_by(Course.id.desc()))).scalars().all()
    else:
        assigned_ids = list(enr_map.keys())
        cond = Course.is_public.is_(True)
        if assigned_ids:
            cond = or_(Course.is_public.is_(True), Course.id.in_(assigned_ids))
        courses = (await session.execute(select(Course).where(cond).order_by(Course.id.desc()))).scalars().all()

    out = []
    for c in courses:
        e = enr_map.get(c.id)
        out.append({
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "is_mandatory": c.is_mandatory,
            "deadline_days": c.deadline_days,
            "is_public": c.is_public,
            "enrolled": e is not None,
            "status": e.status if e else None,
            "progress_percent": e.progress_percent if e else None,
            "deadline_at": e.deadline_at if e else None,
        })
    return out


@router.put("/lessons/{lesson_id}/progress")
async def save_progress(
    lesson_id: int,
    payload: VideoProgressIn,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    # MVP-валидация против "читерства" углубим позже (нужны длительности видео/сессии)
    vp = (await session.execute(
        select(VideoProgress).where(VideoProgress.user_id == user.id, VideoProgress.lesson_id == lesson_id)
    )).scalar_one_or_none()

    if not vp:
        vp = VideoProgress(user_id=user.id, lesson_id=lesson_id)
        session.add(vp)

    vp.position_sec = payload.position_sec
    vp.watched_percent = payload.watched_percent

    await session.commit()
    return {"ok": True}
@router.post("/assign")
async def assign_course(
    payload: dict,
    session: AsyncSession = Depends(get_session),
    _=Depends(require_roles(Role.ADMIN.value)),
):
    user_id = int(payload.get("user_id"))
    course_id = int(payload.get("course_id"))

    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    course = (await session.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    exists = (
        await session.execute(
            select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Already assigned")

    deadline_at = None
    if getattr(course, "deadline_days", None):
        deadline_at = datetime.now(timezone.utc) + timedelta(days=course.deadline_days)

    enr = Enrollment(
        user_id=user_id,
        course_id=course_id,
        status=EnrollmentStatus.ASSIGNED.value,
        progress_percent=0,
        deadline_at=deadline_at,
    )
    session.add(enr)
    await session.commit()
    return {"ok": True}