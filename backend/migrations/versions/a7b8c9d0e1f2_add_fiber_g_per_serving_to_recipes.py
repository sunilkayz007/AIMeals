"""add fiber_g_per_serving to recipes

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-08-20 00:00:00.000000

Notes:
    Hand-written, same reasoning as the prior migrations
    this month. Nullable column, matches
    water_ml_per_serving's treatment — no backfill/default
    concerns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'recipes',
        sa.Column('fiber_g_per_serving', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('recipes', 'fiber_g_per_serving')