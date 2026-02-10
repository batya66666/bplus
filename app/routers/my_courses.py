from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_roles
from app.models.core import Course, Lesson, Enrollment, LessonCompletion
from app.models.enums import Role, EnrollmentStatus
from app.schemas.my_courses import MyCourseOut, LessonOut, CompleteLessonIn

router = APIRouter()

@router.get("", response_model=list[MyCourseOut])
async def my_courses(
    session: AsyncSession = Depends(get_session),
    me=Depends(require_roles(Role.ADMIN.value, Role.MENTOR.value, Role.EMPLOYEE.value, Role.TEAM_LEAD.value, Role.LD_MANAGER.value)),
):
    # enrollments пользователя
    enrolls = (
        await session.execute(
            select(Enrollment).where(Enrollment.user_id == me.id)
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
    enroll_map = {e.course_id: e for e in enrolls}

    lessons = (
        await session.execute(
            select(Lesson).where(Lesson.course_id.in_(course_ids)).order_by(Lesson.course_id.asc(), Lesson.order.asc())
        )
    ).scalars().all()

    # completions
    comp_rows = (
        await session.execute(
            select(LessonCompletion.lesson_id).where(LessonCompletion.user_id == me.id)
        )
    ).scalars().all()
    completed_set = set(comp_rows)

    # группируем уроки по курсу
    by_course = {}
    for ls in lessons:
        by_course.setdefault(ls.course_id, []).append(ls)

    out: list[MyCourseOut] = []

    for cid in course_ids:
        c = course_map.get(cid)
        e = enroll_map.get(cid)
        if not c or not e:
            continue

        ls_list = by_course.get(cid, [])
        total = len(ls_list)
        done = sum(1 for l in ls_list if l.id in completed_set)
        progress = int((done / total) * 100) if total else 0

        # обновим статус по прогрессу (по ТЗ: завершено = read-only)
        if progress >= 100:
            e.status = EnrollmentStatus.COMPLETED.value
            e.progress_percent = 100
        elif progress > 0 and e.status == EnrollmentStatus.ASSIGNED.value:
            e.status = EnrollmentStatus.IN_PROGRESS.value
            e.progress_percent = progress
        else:
            e.progress_percent = progress

        await session.commit()

        out.append(
            MyCourseOut(
                course_id=c.id,
                title=c.title,
                description=c.description,
                is_mandatory=c.is_mandatory,
                status=e.status,
                progress_percent=e.progress_percent,
                deadline_at=e.deadline_at,
                lessons=[
                    LessonOut(
                        id=l.id,
                        order=l.order,
                        title=l.title,
                        is_completed=(l.id in completed_set),
                    )
                    for l in ls_list
                ],
            )
        )

    return out


@router.post("/complete_lesson")
async def complete_lesson(
    payload: CompleteLessonIn,
    session: AsyncSession = Depends(get_session),
    me=Depends(require_roles(Role.ADMIN.value, Role.MENTOR.value, Role.EMPLOYEE.value, Role.TEAM_LEAD.value, Role.LD_MANAGER.value)),
):
    lesson = (await session.execute(select(Lesson).where(Lesson.id == payload.lesson_id))).scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # проверим, что курс назначен пользователю
    enr = (
        await session.execute(
            select(Enrollment).where(Enrollment.user_id == me.id, Enrollment.course_id == lesson.course_id)
        )
    ).scalar_one_or_none()
    if not enr:
        raise HTTPException(status_code=403, detail="Course not assigned")

    if enr.status == EnrollmentStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Course already completed")

    existing = (
        await session.execute(
            select(LessonCompletion).where(LessonCompletion.user_id == me.id, LessonCompletion.lesson_id == lesson.id)
        )
    ).scalar_one_or_none()

    if payload.completed:
        if not existing:
            session.add(LessonCompletion(user_id=me.id, lesson_id=lesson.id))
            await session.commit()
    else:
        if existing:
            await session.delete(existing)
            await session.commit()

    return {"ok": True}
