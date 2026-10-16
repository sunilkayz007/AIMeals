"""add micronutrients to nutrition_logs

Revision ID: c9d0e1f2a3b4
Revises: b3c4d5e6f7a8
Create Date: 2026-08-27 00:00:00.000000

Notes:
    Hand-written, same reasoning as every migration this
    month — avoiding autogenerate. Nullable JSONB column,
    holds all 10 tracked micronutrients as one dict (see
    app/core/micronutrients.py) rather than one column per
    nutrient — no backfill/default needed since it's nullable
    and a missing value is treated as "no data" (all zeros
    when read), same semantics fiber_g's rollout established
    would have needed 10x the migrations to replicate per-column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'nutrition_logs',
        sa.Column('micronutrients', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('nutrition_logs', 'micronutrients')
