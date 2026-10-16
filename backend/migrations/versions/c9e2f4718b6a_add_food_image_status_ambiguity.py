"""add status and ambiguity to food_images

Revision ID: c9e2f4718b6a
Revises: b7d4e619a305
Create Date: 2026-07-31

=========================================================
AIMeals Backend
Migration: Add status/ambiguity to food_images

Purpose:
    Adds the food_image_status enum type and two new columns
    supporting the one-item clarification flow: status
    (PENDING while awaiting the user's answer to an ambiguous
    item, CONFIRMED once finalized) and ambiguity (JSONB
    holding the question + all pre-computed alternative
    nutrition estimates).

    This CREATEs a new enum type from scratch, which does NOT
    need autocommit_block() — that restriction only applies to
    ALTER TYPE ... ADD VALUE on an EXISTING type, not to
    creating a brand new one.

    Existing rows (all already-finalized analyses from before
    this flow existed) are backfilled to status=CONFIRMED via
    server_default, so nothing breaks for historical data.
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c9e2f4718b6a"
down_revision = "b7d4e619a305"
branch_labels = None
depends_on = None

food_image_status_enum = postgresql.ENUM(
    "PENDING", "CONFIRMED", name="food_image_status"
)


def upgrade() -> None:
    food_image_status_enum.create(op.get_bind())

    op.add_column(
        "food_images",
        sa.Column(
            "status",
            sa.Enum("PENDING", "CONFIRMED", name="food_image_status"),
            nullable=False,
            server_default="CONFIRMED",
        ),
    )
    op.add_column(
        "food_images",
        sa.Column("ambiguity", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("food_images", "ambiguity")
    op.drop_column("food_images", "status")
    food_image_status_enum.drop(op.get_bind())