from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_roles
from app.models.core import Course, Lesson, Enrollment, LessonCompletion, VideoProgress
from app.models.enums import Role, EnrollmentStatus
from app.schemas.my_courses import MyCourseOut, LessonOut, CompleteLessonIn, LessonDetailOut, VideoProgressIn

router = APIRouter()


@router.get("", response_model=list[MyCourseOut])
async def my_courses(
        session: AsyncSession = Depends(get_session),
        me=Depends(require_roles(Role.ADMIN.value, Role.MENTOR.value, Role.EMPLOYEE.value, Role.TEAM_LEAD.value,
                                 Role.LD_MANAGER.value)),
):
    """Получить список всех курсов пользователя с уроками"""
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

        # обновим статус по прогрессу
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


# ========== ВИДЕОПЛЕЕР: ПОЛУЧИТЬ ДЕТАЛИ УРОКА ==========

@router.get("/lessons/{lesson_id}", response_model=LessonDetailOut)
async def get_lesson_details(
        lesson_id: int,
        session: AsyncSession = Depends(get_session),
        me=Depends(require_roles(Role.ADMIN.value, Role.MENTOR.value, Role.EMPLOYEE.value, Role.TEAM_LEAD.value,
                                 Role.LD_MANAGER.value)),
):
    """Получить полную информацию об уроке (для плеера)"""
    # Получаем урок
    lesson = await session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден")

    # Проверяем, открыт ли этот урок (пройден ли предыдущий)
    if lesson.order > 1:
        prev_lesson_query = await session.execute(
            select(LessonCompletion).join(Lesson).where(
                Lesson.course_id == lesson.course_id,
                Lesson.order == lesson.order - 1,
                LessonCompletion.user_id == me.id
            )
        )
        if not prev_lesson_query.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Предыдущий урок не завершен")

    # Получаем сохраненный прогресс видео
    progress_query = await session.execute(
        select(VideoProgress).where(
            VideoProgress.lesson_id == lesson_id,
            VideoProgress.user_id == me.id
        )
    )
    progress = progress_query.scalar_one_or_none()

    # Проверяем, завершен ли урок совсем
    completion_query = await session.execute(
        select(LessonCompletion).where(
            LessonCompletion.lesson_id == lesson_id,
            LessonCompletion.user_id == me.id
        )
    )
    is_completed = completion_query.scalar_one_or_none() is not None

    return {
        "id": lesson.id,
        "title": lesson.title,
        "video_url": lesson.video_url,
        "content": lesson.content,
        "order": lesson.order,
        "current_position_sec": progress.position_sec if progress else 0,
        "is_completed": is_completed
    }


# ========== ВИДЕОПЛЕЕР: ПОЛУЧИТЬ ПРОГРЕСС ==========

@router.get("/lessons/{lesson_id}/progress")
async def get_lesson_progress(
        lesson_id: int,
        session: AsyncSession = Depends(get_session),
        me=Depends(require_roles(Role.ADMIN.value, Role.MENTOR.value, Role.EMPLOYEE.value, Role.TEAM_LEAD.value,
                                 Role.LD_MANAGER.value)),
):
    """Получить сохраненный прогресс просмотра видео"""
    progress = (
        await session.execute(
            select(VideoProgress).where(
                VideoProgress.user_id == me.id,
                VideoProgress.lesson_id == lesson_id
            )
        )
    ).scalar_one_or_none()

    if not progress:
        return {"position_sec": 0, "watched_percent": 0}

    return {
        "position_sec": progress.position_sec,
        "watched_percent": progress.watched_percent
    }


# ========== ВИДЕОПЛЕЕР: ОБНОВИТЬ ПРОГРЕСС ==========

@router.post("/lessons/{lesson_id}/progress")
async def save_lesson_progress(
        lesson_id: int,
        data: VideoProgressIn,
        session: AsyncSession = Depends(get_session),
        me=Depends(require_roles(Role.ADMIN.value, Role.MENTOR.value, Role.EMPLOYEE.value, Role.TEAM_LEAD.value,
                                 Role.LD_MANAGER.value)),
):
    """Сохранить прогресс просмотра видео (вызывается каждые 5-10 сек)"""

    # Пытаемся найти существующую запись
    query = select(VideoProgress).where(
        VideoProgress.lesson_id == lesson_id,
        VideoProgress.user_id == me.id
    )
    result = await session.execute(query)
    progress = result.scalar_one_or_none()

    if progress:
        # Обновляем существующий прогресс
        progress.position_sec = data.position_sec
        # watched_percent только растет (защита от читерства)
        progress.watched_percent = max(progress.watched_percent, data.watched_percent)
    else:
        # Создаем новую запись
        new_progress = VideoProgress(
            user_id=me.id,
            lesson_id=lesson_id,
            position_sec=data.position_sec,
            watched_percent=data.watched_percent
        )
        session.add(new_progress)

    await session.commit()
    return {"status": "ok"}


# ========== ЗАВЕРШИТЬ УРОК ==========

@router.post("/complete_lesson")
async def complete_lesson_endpoint(
        payload: CompleteLessonIn,
        session: AsyncSession = Depends(get_session),
        me=Depends(require_roles(Role.ADMIN.value, Role.MENTOR.value, Role.EMPLOYEE.value, Role.TEAM_LEAD.value,
                                 Role.LD_MANAGER.value)),
):
    """Отметить урок как завершенный (вызывается при клике 'Далее')"""

    lesson = (await session.execute(select(Lesson).where(Lesson.id == payload.lesson_id))).scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Проверим, что курс назначен пользователю
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
        # Отмечаем как пройденный
        if not existing:
            session.add(LessonCompletion(user_id=me.id, lesson_id=lesson.id))
            await session.commit()

            # Пересчитываем прогресс курса
            await recalculate_course_progress(session, me.id, lesson.course_id)
    else:
        # Снимаем отметку
        if existing:
            await session.delete(existing)
            await session.commit()

            # Пересчитываем прогресс курса
            await recalculate_course_progress(session, me.id, lesson.course_id)

    return {"ok": True}


# ========== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ: ПЕРЕСЧЕТ ПРОГРЕССА ==========

async def recalculate_course_progress(session: AsyncSession, user_id: int, course_id: int):
    """Пересчитывает прогресс курса на основе завершенных уроков"""

    # Считаем общее количество уроков в курсе
    total_lessons_res = await session.execute(
        select(func.count(Lesson.id)).where(Lesson.course_id == course_id)
    )
    total_count = total_lessons_res.scalar() or 0

    # Считаем сколько уроков юзер прошел в этом курсе
    completed_lessons_res = await session.execute(
        select(func.count(LessonCompletion.id))
        .join(Lesson, Lesson.id == LessonCompletion.lesson_id)
        .where(Lesson.course_id == course_id, LessonCompletion.user_id == user_id)
    )
    completed_count = completed_lessons_res.scalar() or 0

    # Считаем процент
    new_percent = int((completed_count / total_count) * 100) if total_count > 0 else 0

    # Обновляем таблицу Enrollments
    await session.execute(
        update(Enrollment)
        .where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .values(progress_percent=new_percent)
    )

    await session.commit()

