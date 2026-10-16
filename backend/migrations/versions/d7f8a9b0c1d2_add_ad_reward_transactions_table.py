"""add ad_reward_transactions table (superseded — now a no-op)

Revision ID: d7f8a9b0c1d2
Revises: c1a2b3d4e5f6
Create Date: 2026-08-19 00:00:00.000000

Notes:
    SUPERSEDED. This migration originally created the
    ad_reward_transactions table with an early schema
    (reward_amount column, user_id NOT NULL, ON DELETE CASCADE).

    That table shape was replaced before it was ever relied on
    in production by migration l8g9h0i1j2k3 (Aug 31), which
    creates the same table with the schema the app actually uses
    (no reward_amount column, user_id nullable, ON DELETE SET
    NULL) and is the one AdRewardTransactionRepository.
    record_if_new() depends on.

    Both migrations were accidentally left in the chain, so a
    fresh-DB deploy (`alembic upgrade head` against an empty
    database) would create the table here and then fail on
    l8g9h0i1j2k3 with "relation already exists". This migration
    is now a deliberate no-op — kept in place (rather than
    deleted) so it doesn't shift the revision graph for any
    environment that already ran the original version — and
    l8g9h0i1j2k3 remains the single source of truth for this
    table going forward.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd7f8a9b0c1d2'
down_revision: Union[str, Sequence[str], None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op — see module docstring. Superseded by l8g9h0i1j2k3."""
    pass


def downgrade() -> None:
    """No-op — see module docstring. Superseded by l8g9h0i1j2k3."""
    pass
