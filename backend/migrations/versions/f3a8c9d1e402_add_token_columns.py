"""add input_tokens and output_tokens to ai_interactions

Revision ID: f3a8c9d1e402
Revises: a21f358b28ad
Create Date: 2026-07-31

=========================================================
AIMeals Backend
Migration: Add input_tokens / output_tokens to ai_interactions

Purpose:
    Adds two new nullable columns so per-user dollar cost can
    be calculated accurately. tokens_used (the existing
    combined total) is left untouched for backward
    compatibility — nothing that reads it breaks.

    This is a plain ADD COLUMN — no autocommit_block() needed,
    since adding a nullable column doesn't have Postgres's
    transactional-DDL restriction that ALTER TYPE ... ADD
    VALUE has.
=========================================================
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3a8c9d1e402"
down_revision = "a21f358b28ad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_interactions",
        sa.Column("input_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "ai_interactions",
        sa.Column("output_tokens", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_interactions", "output_tokens")
    op.drop_column("ai_interactions", "input_tokens")