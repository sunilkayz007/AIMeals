"""add allergen_deep_insight to interaction_type enum

Revision ID: d1a6c8e2f5b9
Revises: b7e2f9a4d3c6
Create Date: 2026-08-06

=========================================================
AIMeals Backend
Migration: Add allergen_deep_insight to interaction_type

Purpose:
    InteractionType.ALLERGEN_DEEP_INSIGHT was added to the
    Python enum in app/models/ai_interaction.py, but
    interaction_type is a native Postgres enum type — adding
    a Python enum member alone does NOT alter the database
    type. This migration adds the matching value there.

    ALTER TYPE ... ADD VALUE cannot run inside a normal
    transaction block in Postgres, so this uses Alembic's
    autocommit_block() rather than op.execute() directly.

    No downgrade: Postgres does not support removing a value
    from an existing enum type (would require recreating the
    type entirely and remapping every column that uses it) —
    downgrade() is a documented no-op, consistent with how
    enum-value-only migrations are generally handled.
=========================================================
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "d1a6c8e2f5b9"
down_revision = "b7e2f9a4d3c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE interaction_type ADD VALUE IF NOT EXISTS 'allergen_deep_insight'")


def downgrade() -> None:
    # Intentional no-op — see module docstring.
    pass