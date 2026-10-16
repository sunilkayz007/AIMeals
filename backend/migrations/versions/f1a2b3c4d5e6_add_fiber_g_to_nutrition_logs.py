"""add fiber_g to nutrition_logs

Revision ID: f1a2b3c4d5e6
Revises: e3f4a5b6c7d8
Create Date: 2026-08-20 00:00:00.000000

Notes:
    Hand-written, same reasoning as the prior three
    migrations this month: avoiding autogenerate given the
    unrelated schema-drift items it kept mixing in. This
    migration contains ONLY the new nutrition_logs.fiber_g
    column.

    Uses a server_default of '0' during ADD COLUMN so
    existing rows backfill safely (nutrition_logs is a
    populated table, and fiber_g is NOT NULL) — same
    approach as c1a2b3d4e5f6 (bonus_credits_balance). The
    server_default is dropped afterward so it behaves purely
    as the Python model's default=0.0 going forward.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'nutrition_logs',
        sa.Column(
            'fiber_g',
            sa.Float(),
            nullable=False,
            server_default='0',
        ),
    )
    op.alter_column('nutrition_logs', 'fiber_g', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('nutrition_logs', 'fiber_g')