"""make food_images.image_url nullable

Revision ID: b7d4e619a305
Revises: f3a8c9d1e402
Create Date: 2026-07-31

=========================================================
AIMeals Backend
Migration: Make food_images.image_url nullable

Purpose:
    Raw food photos are no longer saved to disk at all —
    AIService.analyze_food_image() now sends image bytes
    directly to Claude and discards them, keeping only the
    extracted structured data. image_url can never be
    populated anymore, so its NOT NULL constraint must be
    dropped or every new row would fail to insert.

    The column itself is kept (not dropped) for forward
    compatibility — see food_image.py's model docstring.
=========================================================
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7d4e619a305"
down_revision = "f3a8c9d1e402"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "food_images",
        "image_url",
        existing_type=sa.String(length=500),
        nullable=True,
    )


def downgrade() -> None:
    # NOTE: if any rows have image_url = NULL at downgrade
    # time (which, going forward, will be ALL of them), this
    # will fail — that's intentional. A downgrade that silently
    # deleted or fabricated data for those rows would be worse
    # than a downgrade that stops and makes you decide what to
    # do with them by hand.
    op.alter_column(
        "food_images",
        "image_url",
        existing_type=sa.String(length=500),
        nullable=False,
    )