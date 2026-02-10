from __future__ import annotations
from app.models.core import User, Course, Enrollment
from datetime import datetime, timedelta, timezone
import asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.db import async_session
from app.models.core import (
    Department,
    User,
    Course,
    Lesson,
    Enrollment,
    Document,
)
from app.models.enums import Role, EnrollmentStatus
from app.security.passwords import hash_password


async def get_or_create_department(name: str) -> Department:
    async with async_session() as session:
        dep = (await session.execute(select(Department).where(Department.name == name))).scalar_one_or_none()
        if dep:
            return dep
        dep = Department(name=name)
        session.add(dep)
        await session.commit()
        await session.refresh(dep)
        return dep


async def get_or_create_user(
    email: str,
    full_name: str,
    role: Role,
    password: str,
    department_id: int | None = None,
) -> User:
    async with async_session() as session:
        u = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if u:
            # обновим роль/ФИО/отдел (удобно при повторном сидировании)
            u.full_name = full_name
            u.role = role.value
            u.department_id = department_id
            if not u.password_hash:
                u.password_hash = hash_password(password)
            await session.commit()
            await session.refresh(u)
            return u

        u = User(
            email=email,
            full_name=full_name,
            role=role.value,
            department_id=department_id,
            password_hash=hash_password(password),
            is_active=True,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u


async def get_or_create_course(title: str, description: str, is_mandatory: bool, deadline_days: int) -> Course:
    async with async_session() as session:
        c = (await session.execute(select(Course).where(Course.title == title))).scalar_one_or_none()
        if c:
            c.description = description
            c.is_mandatory = is_mandatory
            c.deadline_days = deadline_days
            await session.commit()
            await session.refresh(c)
            return c

        c = Course(title=title, description=description, is_mandatory=is_mandatory, deadline_days=deadline_days)
        session.add(c)
        await session.commit()
        await session.refresh(c)
        return c


async def ensure_lessons(course_id: int, lessons: list[dict]) -> None:
    async with async_session() as session:
        for item in lessons:
            order = int(item["order"])
            title = str(item["title"])
            video_url = item.get("video_url")
            content = item.get("content")

            exists = (
                await session.execute(
                    select(Lesson).where(Lesson.course_id == course_id, Lesson.order == order)
                )
            ).scalar_one_or_none()

            if exists:
                exists.title = title
                exists.video_url = video_url
                exists.content = content
            else:
                session.add(
                    Lesson(
                        course_id=course_id,
                        order=order,
                        title=title,
                        video_url=video_url,
                        content=content,
                    )
                )

        await session.commit()


async def ensure_enrollment(user_id: int, course_id: int, deadline_days: int) -> None:
    async with async_session() as session:
        e = (
            await session.execute(
                select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            )
        ).scalar_one_or_none()
        if e:
            # обновим дедлайн при повторном запуске
            if deadline_days > 0:
                e.deadline_at = datetime.now(timezone.utc) + timedelta(days=deadline_days)
            await session.commit()
            return

        deadline_at = None
        if deadline_days > 0:
            deadline_at = datetime.now(timezone.utc) + timedelta(days=deadline_days)

        e = Enrollment(
            user_id=user_id,
            course_id=course_id,
            status=EnrollmentStatus.ASSIGNED.value,
            progress_percent=0,
            deadline_at=deadline_at,
        )
        session.add(e)
        await session.commit()


async def ensure_documents(docs: list[dict]) -> None:
    async with async_session() as session:
        for d in docs:
            title = d["title"]
            file_url = d["file_url"]
            category = d.get("category", "HR")
            access_level = d.get("access_level", "All")

            exists = (await session.execute(select(Document).where(Document.title == title))).scalar_one_or_none()
            if exists:
                exists.file_url = file_url
                exists.category = category
                exists.access_level = access_level
            else:
                session.add(
                    Document(
                        title=title,
                        file_url=file_url,
                        category=category,
                        access_level=access_level,
                    )
                )
        await session.commit()

async def seed_enrollments(session):
    users = (await session.execute(select(User))).scalars().all()
    courses = (await session.execute(select(Course).where(Course.is_mandatory == True))).scalars().all()

    for u in users:
        for c in courses:
            exists = (
                await session.execute(
                    select(Enrollment).where(
                        Enrollment.user_id == u.id,
                        Enrollment.course_id == c.id,
                    )
                )
            ).scalar_one_or_none()

            if exists:
                continue

            deadline = None
            if c.deadline_days:
                deadline = datetime.now(timezone.utc) + timedelta(days=c.deadline_days)

            session.add(
                Enrollment(
                    user_id=u.id,
                    course_id=c.id,
                    status=EnrollmentStatus.ASSIGNED.value,
                    progress_percent=0,
                    deadline_at=deadline,
                )
            )

    await session.commit()
async def seed() -> None:
    # --- Departments ---
    dep_hr = await get_or_create_department("HR")
    dep_it = await get_or_create_department("IT")
    dep_sales = await get_or_create_department("Sales")

    # --- Users (пароли для демо) ---
    # Можно логиниться ими на фронте
    admin = await get_or_create_user(
        email="admin@local",
        full_name="System Admin",
        role=Role.ADMIN,
        password="admin12345",
        department_id=dep_it.id,
    )
    mentor = await get_or_create_user(
        email="mentor@local",
        full_name="Main Mentor",
        role=Role.MENTOR,
        password="mentor12345",
        department_id=dep_it.id,
    )
    employee = await get_or_create_user(
        email="employee@local",
        full_name="New Employee",
        role=Role.EMPLOYEE,
        password="employee12345",
        department_id=dep_sales.id,
    )
    team_lead = await get_or_create_user(
        email="lead@local",
        full_name="Team Lead",
        role=Role.TEAM_LEAD,
        password="lead12345",
        department_id=dep_sales.id,
    )
    ld_manager = await get_or_create_user(
        email="ld@local",
        full_name="L&D Manager",
        role=Role.LD_MANAGER,
        password="ld12345",
        department_id=dep_hr.id,
    )

    # --- Courses ---
    c1 = await get_or_create_course(
        title="Введение в компанию",
        description="Онбординг: процессы, коммуникации, правила.",
        is_mandatory=True,
        deadline_days=7,
    )
    c2 = await get_or_create_course(
        title="Информационная безопасность",
        description="Базовые практики безопасности, пароли, фишинг, доступы.",
        is_mandatory=True,
        deadline_days=10,
    )
    c3 = await get_or_create_course(
        title="Командная работа и стендапы",
        description="Как писать ежедневные отчёты, формат и ожидания.",
        is_mandatory=False,
        deadline_days=0,
    )

    # --- Lessons ---
    await ensure_lessons(
        c1.id,
        [
            {"order": 1, "title": "Добро пожаловать", "video_url": None, "content": "Кто мы и как работаем."},
            {"order": 2, "title": "Коммуникации", "video_url": None, "content": "Каналы, правила, этикет."},
            {"order": 3, "title": "Первые 7 дней", "video_url": None, "content": "Чеклист онбординга."},
        ],
    )
    await ensure_lessons(
        c2.id,
        [
            {"order": 1, "title": "Пароли и MFA", "video_url": None, "content": "Длина, менеджеры паролей, MFA."},
            {"order": 2, "title": "Фишинг", "video_url": None, "content": "Как распознать, что делать."},
        ],
    )
    await ensure_lessons(
        c3.id,
        [
            {"order": 1, "title": "Формат стендапа", "video_url": None, "content": "Сделал / План / Блокеры."},
            {"order": 2, "title": "Ревью от ментора", "video_url": None, "content": "Когда возвращаем на доработку."},
        ],
    )

    # --- Enrollments (назначим сотруднику обязательные курсы) ---
    await ensure_enrollment(employee.id, c1.id, deadline_days=c1.deadline_days)
    await ensure_enrollment(employee.id, c2.id, deadline_days=c2.deadline_days)
    await ensure_enrollment(employee.id, c3.id, deadline_days=c3.deadline_days)

    # --- Documents ---
    await ensure_documents(
        [
            {
                "title": "Регламент: Рабочие коммуникации",
                "file_url": "https://example.com/docs/communications.pdf",
                "category": "HR",
                "access_level": "All",
            },
            {
                "title": "Регламент: ИБ (Security)",
                "file_url": "https://example.com/docs/security.pdf",
                "category": "IT",
                "access_level": "All",
            },
            {
                "title": "Политика доступа к системам",
                "file_url": "https://example.com/docs/access-policy.pdf",
                "category": "IT",
                "access_level": "Admins Only",
            },
        ]
    )

    print("✅ SEED DONE")
    print("Логины для фронта:")
    print(" - admin@local.test / admin12345")
    print(" - mentor@local.test / mentor12345")
    print(" - employee@local.test / employee12345")
    print(" - lead@local.test / lead12345")
    print(" - ld@local.test / ld12345")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
