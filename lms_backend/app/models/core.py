from __future__ import annotations

from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, UniqueConstraint, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UniqueConstraint, ForeignKey
from datetime import datetime, timezone
from app.db import Base
from app.models.enums import Role, EnrollmentStatus, ReportStatus


class DailyReportRevision(Base):
    __tablename__ = "daily_report_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("daily_reports.id", ondelete="CASCADE"), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    text_done: Mapped[str] = mapped_column(Text, nullable=False)
    text_plan: Mapped[str] = mapped_column(Text, nullable=False)
    text_blockers: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(Text, nullable=False)
    mentor_comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=Role.EMPLOYEE.value)

    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    department: Mapped[Department | None] = relationship()

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Login protection
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Streak(Base):
    __tablename__ = "streaks"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_streak_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deadline_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Lesson(Base):
    __tablename__ = "lessons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Lesson")
    video_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("course_id", "order", name="uq_lessons_course_order"),)


class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default=EnrollmentStatus.ASSIGNED.value)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollments_user_course"),)


class VideoProgress(Base):
    __tablename__ = "video_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False, index=True)

    # seconds
    position_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watched_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_video_user_lesson"),)


class DailyReport(Base):
    __tablename__ = "daily_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)

    text_done: Mapped[str] = mapped_column(Text, nullable=False)
    text_plan: Mapped[str] = mapped_column(Text, nullable=False)
    text_blockers: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ReportStatus.PENDING.value)
    mentor_comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="HR")
    access_level: Mapped[str] = mapped_column(String(64), nullable=False, default="All")


class LessonCompletion(Base):
    __tablename__ = "lesson_completions"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_completion"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    completed_at: Mapped[datetime] = mapped_column(default=datetime.now)

    user = relationship("User")
    lesson = relationship("Lesson")

