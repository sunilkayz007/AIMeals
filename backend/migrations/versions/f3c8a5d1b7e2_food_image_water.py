"""food image total_water_ml

Revision ID: f3c8a5d1b7e2
Revises: e9f4b1c7a2d8
Create Date: 2026-08-07

=========================================================
AIMeals Backend
Migration: Food Image Water

Purpose:
    Closes the previously-flagged gap where scanned meals
    (Food Image Analysis) contributed 0 to daily water totals.
    Adds total_water_ml to food_images, mirroring
    recipes.water_ml_per_serving and nutrition_logs.water_ml —
    same nullable Float pattern, summed from Claude's per-item
    water_ml estimates in AIService.analyze_food_image()
    (not asked as a separate aggregate, so it can't drift out
    of sync with the per-item breakdown).
=========================================================
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3c8a5d1b7e2"
down_revision = "e9f4b1c7a2d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("food_images", sa.Column("total_water_ml", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("food_images", "total_water_ml")