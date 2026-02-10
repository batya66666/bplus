"""init

Revision ID: 0001_init
Revises:
Create Date: 2026-02-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "streaks",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_streak_date", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deadline_days", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="Lesson"),
        sa.Column("video_url", sa.String(length=1000), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.UniqueConstraint("course_id", "order", name="uq_lessons_course_order"),
    )

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ASSIGNED"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "course_id", name="uq_enrollments_user_course"),
    )

    op.create_table(
        "video_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("position_sec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("watched_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_video_user_lesson"),
    )

    op.create_table(
        "daily_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("text_done", sa.Text(), nullable=False),
        sa.Column("text_plan", sa.Text(), nullable=False),
        sa.Column("text_blockers", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("mentor_comment", sa.Text(), nullable=True),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=1000), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="HR"),
        sa.Column("access_level", sa.String(length=64), nullable=False, server_default="All"),
    )


def downgrade():
    op.drop_table("documents")
    op.drop_table("daily_reports")
    op.drop_table("video_progress")
    op.drop_table("enrollments")
    op.drop_table("lessons")
    op.drop_table("courses")
    op.drop_table("streaks")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("departments")
