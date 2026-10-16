"""nutrition log food-image linking, portion tracking, and confirmation dismissals

Revision ID: f291b7c3d8a4
Revises: e7c4a83f5b19
Create Date: 2026-08-05

=========================================================
AIMeals Backend
Migration: Nutrition log food-image linking + portions + dismissals

Purpose:
    Supports the "did you eat this?" soft-prompt feature:
    - nutrition_logs gets `food_image_id` (nullable FK, same
      SET NULL pattern as recipe_id — a log entry can now
      trace back to the food-image scan it came from) and
      `portion_percentage` (float, default 100.0 — how much
      of the recipe/scan was actually consumed; existing rows
      backfill to 100.0, meaning "the whole thing," which is
      the correct historical assumption for entries logged
      before this feature existed).
    - New table `meal_confirmation_dismissals` — records when
      a user explicitly says "No" (or skips) a soft-prompt
      about a specific recipe or food-image scan, so that item
      stops being asked about again. Exactly one of
      recipe_id/food_image_id is set per row (never both) —
      not enforced at the DB level (no CHECK constraint),
      trusted to the service layer, consistent with how this
      codebase already handles nullable dual-FK rows (see
      AllergenOverrideConsent).
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f291b7c3d8a4"
down_revision = "e7c4a83f5b19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------
    # nutrition_logs: food_image_id + portion_percentage
    # ---------------------------------------------------
    op.add_column(
        "nutrition_logs",
        sa.Column(
            "food_image_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("food_images.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_nutrition_logs_food_image_id",
        "nutrition_logs",
        ["food_image_id"],
    )
    op.add_column(
        "nutrition_logs",
        sa.Column(
            "portion_percentage",
            sa.Float(),
            nullable=False,
            server_default="100.0",
        ),
    )

    # ---------------------------------------------------
    # meal_confirmation_dismissals: new table
    # ---------------------------------------------------
    op.create_table(
        "meal_confirmation_dismissals",
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
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "food_image_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("food_images.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_meal_confirmation_dismissals_user_id",
        "meal_confirmation_dismissals",
        ["user_id"],
    )
    op.create_index(
        "ix_meal_confirmation_dismissals_recipe_id",
        "meal_confirmation_dismissals",
        ["recipe_id"],
    )
    op.create_index(
        "ix_meal_confirmation_dismissals_food_image_id",
        "meal_confirmation_dismissals",
        ["food_image_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meal_confirmation_dismissals_food_image_id",
        table_name="meal_confirmation_dismissals",
    )
    op.drop_index(
        "ix_meal_confirmation_dismissals_recipe_id",
        table_name="meal_confirmation_dismissals",
    )
    op.drop_index(
        "ix_meal_confirmation_dismissals_user_id",
        table_name="meal_confirmation_dismissals",
    )
    op.drop_table("meal_confirmation_dismissals")

    op.drop_column("nutrition_logs", "portion_percentage")
    op.drop_index("ix_nutrition_logs_food_image_id", table_name="nutrition_logs")
    op.drop_column("nutrition_logs", "food_image_id")