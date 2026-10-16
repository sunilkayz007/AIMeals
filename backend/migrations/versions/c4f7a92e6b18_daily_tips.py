"""daily tips cache table

Revision ID: c4f7a92e6b18
Revises: a8d3f61c9e27
Create Date: 2026-08-06

=========================================================
AIMeals Backend
Migration: Daily tips cache table

Purpose:
    Backs the "Tips for you" Home screen feature — a short,
    AI-generated encouraging tip based on the user's remaining
    macros for the day. Cached ONE ROW PER USER PER DAY
    (enforced by the unique constraint below), so repeated
    Home screen loads never trigger more than one Claude call
    per user per day, regardless of how many times the screen
    is opened. See AIService.get_daily_tip()'s docstring for
    the full caching logic.
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c4f7a92e6b18"
down_revision = "a8d3f61c9e27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_tips",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tip_date", sa.Date(), nullable=False),
        sa.Column("tip_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_daily_tips_user_id", "daily_tips", ["user_id"])
    # Enforces the one-tip-per-user-per-day cache guarantee at the
    # database level, not just in application logic — a concurrent
    # double-request can't create two rows for the same day.
    op.create_unique_constraint(
        "uq_daily_tips_user_id_tip_date",
        "daily_tips",
        ["user_id", "tip_date"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_daily_tips_user_id_tip_date", "daily_tips", type_="unique")
    op.drop_index("ix_daily_tips_user_id", table_name="daily_tips")
    op.drop_table("daily_tips")