"""fix HEALTH_REPORT_ANALYSIS casing on interaction_type enum

Revision ID: h4c5d6e7f8g9
Revises: g3b4c5d6e7f8
Create Date: 2026-08-28 00:00:00.000000

Notes:
    Bug fix. The earlier migration (f2a3b4c5d6e7) added
    'health_report_analysis' (lowercase, matching the Python
    enum's .value) to the interaction_type Postgres enum. But
    this app's InteractionType column actually serializes by
    SQLAlchemy's DEFAULT Enum behavior -- the enum member's
    .name (e.g. 'RECIPE_GENERATION'), not .value -- confirmed
    by every other existing interaction_type row already using
    UPPERCASE names. The lowercase value added earlier was
    simply wrong and is never used by the ORM; this migration
    adds the correct uppercase 'HEALTH_REPORT_ANALYSIS' value
    the application actually inserts. The unused lowercase
    value is harmless leftover (Postgres cannot remove enum
    values), left in place rather than attempting a risky
    enum-value removal.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'h4c5d6e7f8g9'
down_revision: Union[str, Sequence[str], None] = 'g3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE interaction_type ADD VALUE IF NOT EXISTS 'HEALTH_REPORT_ANALYSIS'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres does not support removing a value from an enum
    # type -- same accepted asymmetry as the original migration
    # that added this enum's values.
    pass