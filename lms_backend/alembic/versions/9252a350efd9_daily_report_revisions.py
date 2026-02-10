"""daily report revisions

Revision ID: 9252a350efd9
Revises: 0001_init
Create Date: 2026-02-08 17:07:07.326677

"""

from alembic import op
import sqlalchemy as sa

revision = '9252a350efd9'
down_revision = '0001_init'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "daily_report_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("text_done", sa.Text(), nullable=False),
        sa.Column("text_plan", sa.Text(), nullable=False),
        sa.Column("text_blockers", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("mentor_comment", sa.Text(), nullable=True),
    )
    op.create_index("ix_daily_report_revisions_report_id", "daily_report_revisions", ["report_id"])

def downgrade():
    op.drop_index("ix_daily_report_revisions_report_id", table_name="daily_report_revisions")
    op.drop_table("daily_report_revisions")