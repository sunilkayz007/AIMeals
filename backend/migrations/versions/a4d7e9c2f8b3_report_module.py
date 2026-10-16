"""report module

Revision ID: a4d7e9c2f8b3
Revises: f3c8a5d1b7e2
Create Date: 2026-08-08

=========================================================
AIMeals Backend
Migration: Report Module

Purpose:
    Adds the "Report" feature — user-submitted reviews
    (bug/suggestion/complaint/praise) with an admin-reply
    comment thread, for transparency and as a durable
    feedback corpus.
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a4d7e9c2f8b3"
down_revision = "f3c8a5d1b7e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    report_category = postgresql.ENUM(
        "bug", "suggestion", "complaint", "praise",
        name="report_category",
    )
    report_category.create(bind, checkfirst=True)

    report_status = postgresql.ENUM(
        "open", "in_progress", "resolved",
        name="report_status",
    )
    report_status.create(bind, checkfirst=True)

    if "reports" not in inspector.get_table_names():
        op.create_table(
            "reports",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("category", report_category, nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column(
                "status",
                report_status,
                nullable=False,
                server_default="open",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_reports_user_id", "reports", ["user_id"])

    if "report_comments" not in inspector.get_table_names():
        op.create_table(
            "report_comments",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "report_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("reports.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "author_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "is_admin_reply",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("comment_text", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_report_comments_report_id", "report_comments", ["report_id"])


def downgrade() -> None:
    op.drop_index("ix_report_comments_report_id", table_name="report_comments")
    op.drop_table("report_comments")
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_table("reports")

    postgresql.ENUM(name="report_status").drop(op.get_bind())
    postgresql.ENUM(name="report_category").drop(op.get_bind())