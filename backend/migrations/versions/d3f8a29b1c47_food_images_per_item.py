"""rework food_images to per-item detection

Revision ID: d3f8a29b1c47
Revises: c9e2f4718b6a
Create Date: 2026-08-02

=========================================================
AIMeals Backend
Migration: Rework food_images to per-item food detection

Purpose:
    Replaces the single-dish-name + single-ambiguity design
    with per-item detection: a JSONB list of individually
    detected foods, each with its own confidence, macros, and
    (if uncertain) its own independent alternatives — no
    combinatorial explosion, since each item's alternative is
    self-contained rather than requiring whole-dish
    recombination.

    Drops: identified_food_name, estimated_calories,
    estimated_protein_g, estimated_carbs_g, estimated_fat_g,
    ambiguity (the single-item-ambiguity JSONB from the
    previous design).

    Adds: meal_type, detected_foods (JSONB list, each entry
    optionally carrying its own "alternatives" sub-list),
    total_calories, total_protein_g, total_carbs_g, total_fat_g
    (now explicit stored totals, summed from detected_foods
    once resolved, rather than being the only numbers that
    ever existed).

    This is a genuine breaking change to the response shape.
    Made deliberately NOW, before any real frontend/client
    exists — this is the cheapest point in the project's
    lifetime to make this change; doing it later, after a
    real app depends on the old shape, would cost far more.

    Existing rows lose their old single-dish data (acceptable —
    this is pre-production test/dev data only).
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d3f8a29b1c47"
down_revision = "c9e2f4718b6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old single-dish fields.
    op.drop_column("food_images", "identified_food_name")
    op.drop_column("food_images", "estimated_calories")
    op.drop_column("food_images", "estimated_protein_g")
    op.drop_column("food_images", "estimated_carbs_g")
    op.drop_column("food_images", "estimated_fat_g")
    op.drop_column("food_images", "ambiguity")

    # Add the new per-item fields.
    op.add_column("food_images", sa.Column("meal_type", sa.String(length=50), nullable=True))
    op.add_column(
        "food_images",
        sa.Column("detected_foods", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("food_images", sa.Column("total_calories", sa.Float(), nullable=True))
    op.add_column("food_images", sa.Column("total_protein_g", sa.Float(), nullable=True))
    op.add_column("food_images", sa.Column("total_carbs_g", sa.Float(), nullable=True))
    op.add_column("food_images", sa.Column("total_fat_g", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("food_images", "total_fat_g")
    op.drop_column("food_images", "total_carbs_g")
    op.drop_column("food_images", "total_protein_g")
    op.drop_column("food_images", "total_calories")
    op.drop_column("food_images", "detected_foods")
    op.drop_column("food_images", "meal_type")

    op.add_column("food_images", sa.Column("ambiguity", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("food_images", sa.Column("estimated_fat_g", sa.Float(), nullable=True))
    op.add_column("food_images", sa.Column("estimated_carbs_g", sa.Float(), nullable=True))
    op.add_column("food_images", sa.Column("estimated_protein_g", sa.Float(), nullable=True))
    op.add_column("food_images", sa.Column("estimated_calories", sa.Float(), nullable=True))
    op.add_column("food_images", sa.Column("identified_food_name", sa.String(length=255), nullable=True))