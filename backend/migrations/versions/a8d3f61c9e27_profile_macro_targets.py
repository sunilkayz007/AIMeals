"""profile macro targets (protein, carbs, fat)

Revision ID: a8d3f61c9e27
Revises: f291b7c3d8a4
Create Date: 2026-08-05

=========================================================
AIMeals Backend
Migration: Profile macro targets

Purpose:
    Adds manually-set protein_g_target/carbs_g_target/fat_g_target
    to `profiles`, alongside the existing daily_calorie_target.
    Same pattern: nullable, user-set, no AI involved. This is
    deliberately NOT the planned AI-computed macro-target
    feature (still a separate, bigger project) — just extending
    the same simple manual-goal-setting pattern that already
    existed for calories to also cover protein/carbs/fat, so
    the Home screen's progress rings can show real data on both
    sides (consumed from nutrition_logs, target from here)
    without waiting on the AI feature.
=========================================================
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a8d3f61c9e27"
down_revision = "f291b7c3d8a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("protein_g_target", sa.Float(), nullable=True))
    op.add_column("profiles", sa.Column("carbs_g_target", sa.Float(), nullable=True))
    op.add_column("profiles", sa.Column("fat_g_target", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "fat_g_target")
    op.drop_column("profiles", "carbs_g_target")
    op.drop_column("profiles", "protein_g_target")