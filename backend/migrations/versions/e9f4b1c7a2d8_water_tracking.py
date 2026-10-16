"""water tracking — profile targets, recipe/log water fields, water_logs table

Revision ID: e9f4b1c7a2d8
Revises: d1a6c8e2f5b9
Create Date: 2026-08-06

=========================================================
AIMeals Backend
Migration: Water Tracking

Purpose:
    Backs the new water-tracking feature end to end:
      - profiles: daily_water_ml_target, typical_wake_time
      - recipes: water_ml_per_serving (AI-estimated)
      - nutrition_logs: water_ml (scaled, defaults to 0.0)
      - water_logs: new table for manual water entries

    Food-image water is a KNOWN, DELIBERATE gap in this
    migration — models/food_image.py wasn't available when
    this was built, so no total_water_ml column is added to
    food_images here. See NutritionLogService.log_meal_from_
    food_image()'s docstring.
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e9f4b1c7a2d8"
down_revision = "d1a6c8e2f5b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------
    # profiles
    # ---------------------------------------------------
    op.add_column("profiles", sa.Column("daily_water_ml_target", sa.Float(), nullable=True))
    op.add_column("profiles", sa.Column("typical_wake_time", sa.String(length=5), nullable=True))

    # ---------------------------------------------------
    # recipes
    # ---------------------------------------------------
    op.add_column("recipes", sa.Column("water_ml_per_serving", sa.Float(), nullable=True))

    # ---------------------------------------------------
    # nutrition_logs
    # ---------------------------------------------------
    op.add_column(
        "nutrition_logs",
        sa.Column("water_ml", sa.Float(), nullable=False, server_default="0.0"),
    )
    # Drop the server_default after backfilling existing rows —
    # new inserts should rely on the ORM/application default
    # (0.0), not a DB-level default staying on indefinitely,
    # matching how other nullable-with-default columns in this
    # project are handled.
    op.alter_column("nutrition_logs", "water_ml", server_default=None)

    # ---------------------------------------------------
    # water_logs (new table)
    # ---------------------------------------------------
    op.create_table(
        "water_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("logged_at", sa.Date(), nullable=False),
        sa.Column("amount_ml", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_water_logs_user_id", "water_logs", ["user_id"])
    op.create_index("ix_water_logs_logged_at", "water_logs", ["logged_at"])


def downgrade() -> None:
    op.drop_index("ix_water_logs_logged_at", table_name="water_logs")
    op.drop_index("ix_water_logs_user_id", table_name="water_logs")
    op.drop_table("water_logs")

    op.drop_column("nutrition_logs", "water_ml")
    op.drop_column("recipes", "water_ml_per_serving")
    op.drop_column("profiles", "typical_wake_time")
    op.drop_column("profiles", "daily_water_ml_target")