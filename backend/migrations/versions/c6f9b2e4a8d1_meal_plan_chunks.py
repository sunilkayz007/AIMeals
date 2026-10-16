"""meal plan chunks

Revision ID: c6f9b2e4a8d1
Revises: a4d7e9c2f8b3
Create Date: 2026-08-10

=========================================================
AIMeals Backend
Migration: Meal Plan Chunks

Purpose:
    Adds meal_plan_chunks, which tracks per-chunk generation
    state for the pull-based lazy meal plan generation flow —
    large plans are split into CHUNK_SIZE_DAYS-day batches,
    generated as they become due rather than all at once,
    to avoid truncating a single oversized Claude response.
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c6f9b2e4a8d1"
down_revision = "a4d7e9c2f8b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    status_enum = postgresql.ENUM(
        "pending", "completed", "failed",
        name="meal_plan_chunk_status",
    )
    status_enum.create(bind, checkfirst=True)

    if "meal_plan_chunks" not in inspector.get_table_names():
        op.create_table(
            "meal_plan_chunks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "meal_plan_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("meal_plans.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("scheduled_generate_at", sa.Date(), nullable=False),
            sa.Column("meal_types", sa.String(200), nullable=False),
            sa.Column("preferences", sa.Text(), nullable=False, server_default=""),
            sa.Column(
                "status",
                status_enum,
                nullable=False,
                server_default="pending",
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
        op.create_index("ix_meal_plan_chunks_meal_plan_id", "meal_plan_chunks", ["meal_plan_id"])


def downgrade() -> None:
    op.drop_index("ix_meal_plan_chunks_meal_plan_id", table_name="meal_plan_chunks")
    op.drop_table("meal_plan_chunks")
    postgresql.ENUM(name="meal_plan_chunk_status").drop(op.get_bind())