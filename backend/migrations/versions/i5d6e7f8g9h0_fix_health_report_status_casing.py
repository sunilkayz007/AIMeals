"""fix health_report_status enum value casing

Revision ID: i5d6e7f8g9h0
Revises: h4c5d6e7f8g9
Create Date: 2026-08-28 00:00:00.000000

Notes:
    Bug fix -- same class of casing mistake as h4c5d6e7f8g9,
    caught immediately after by testing. The health_report_status
    Postgres enum was created (in f2a3b4c5d6e7) with lowercase
    values ('awaiting_confirmation', 'confirmed') matching the
    Python enum's .value -- but this app's SQLAlchemy Enum
    columns consistently serialize using the enum member's
    UPPERCASE .name instead (confirmed by every other working
    status enum in this app, e.g. FoodImageStatus's rows use
    'PENDING'/'CONFIRMED', not lowercase).

    Uses ALTER TYPE ... RENAME VALUE rather than ADD VALUE,
    since health_reports is a brand-new table with no real
    rows yet (only failed insert attempts from this bug) --
    safe to rename outright rather than leaving an orphaned
    unused lowercase value around, unlike interaction_type
    (an old, heavily-used enum) where renaming existing values
    would have been far riskier.

    RENAME VALUE does not have ADD VALUE's same-transaction
    restriction, so this can run as normal DDL.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'i5d6e7f8g9h0'
down_revision: Union[str, Sequence[str], None] = 'h4c5d6e7f8g9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE health_report_status RENAME VALUE 'awaiting_confirmation' TO 'AWAITING_CONFIRMATION'")
    op.execute("ALTER TYPE health_report_status RENAME VALUE 'confirmed' TO 'CONFIRMED'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE health_report_status RENAME VALUE 'AWAITING_CONFIRMATION' TO 'awaiting_confirmation'")
    op.execute("ALTER TYPE health_report_status RENAME VALUE 'CONFIRMED' TO 'confirmed'")