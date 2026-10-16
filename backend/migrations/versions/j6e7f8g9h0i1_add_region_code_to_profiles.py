"""add region_code to profiles

Revision ID: j6e7f8g9h0i1
Revises: i5d6e7f8g9h0
Create Date: 2026-08-30 00:00:00.000000

Notes:
    Hand-written, same reasoning as every migration this month.
    Nullable string column holding a two-letter ISO region code
    (e.g. "IN", "US"), read from the device's own configured
    locale on the frontend (via expo-localization) -- no location
    permission, no manual "select your country" step. Used as a
    soft regional hint for recipe/meal-plan/coach generation (see
    AIService._build_region_context()) -- never a hard requirement,
    never exposed as a user-facing setting.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j6e7f8g9h0i1'
down_revision: Union[str, Sequence[str], None] = 'i5d6e7f8g9h0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'profiles',
        sa.Column('region_code', sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('profiles', 'region_code')