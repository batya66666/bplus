"""add course is_public

Revision ID: f2412670fa8b
Revises: add_course_is_public
Create Date: 2026-02-08 18:35:12.702345

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f2412670fa8b"
down_revision = "9252a350efd9"   # <-- ВОТ ЭТО ПРАВИЛЬНО
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "courses",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column("courses", "is_public", server_default=None)

def downgrade():
    op.drop_column("courses", "is_public")