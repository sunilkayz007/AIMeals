"""add total_micronutrients to food_images

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-27 00:00:00.000000

Notes:
    Hand-written, same reasoning as the prior migration.
    Nullable JSONB column, the summed total across a scan's
    detected_foods — see app/models/food_image.py's
    total_micronutrients column comment. This is the new
    alembic head after this migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'food_images',
        sa.Column('total_micronutrients', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('food_images', 'total_micronutrients')
