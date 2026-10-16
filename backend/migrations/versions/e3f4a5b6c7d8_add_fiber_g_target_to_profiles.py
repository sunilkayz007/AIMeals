"""add fiber_g_target to profiles

Revision ID: e3f4a5b6c7d8
Revises: d7f8a9b0c1d2
Create Date: 2026-08-20 00:00:00.000000

Notes:
    Hand-written, same reasoning as c1a2b3d4e5f6 and
    d7f8a9b0c1d2: avoiding autogenerate given the unrelated
    schema-drift items it kept mixing in earlier this month.
    This migration contains ONLY the new
    profiles.fiber_g_target column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, Sequence[str], None] = 'd7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'profiles',
        sa.Column('fiber_g_target', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('profiles', 'fiber_g_target')