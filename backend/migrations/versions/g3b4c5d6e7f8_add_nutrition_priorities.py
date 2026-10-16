"""add nutrition_priorities to health_reports

Revision ID: g3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-08-28 00:00:00.000000

Notes:
    Hand-written, same reasoning as every migration this
    month. Nullable JSONB column holding the Nutrition Focus
    Engine's output (Phase 6 of Health Insights) -- a list of
    non-diagnostic nutrition priorities derived from a user's
    CONFIRMED markers. Null until confirm_health_report() runs
    (see app/services/ai_service.py) -- matches
    confirmed_markers' own null-until-confirmed pattern on
    this same table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'g3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'health_reports',
        sa.Column('nutrition_priorities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('health_reports', 'nutrition_priorities')
