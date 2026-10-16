"""add health_reports table and health_report_analysis interaction type

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-27 00:00:00.000000

Notes:
    Hand-written, same reasoning as every migration this
    month. Two parts:

    1. Adds 'health_report_analysis' to the existing
       interaction_type Postgres enum. Postgres requires
       ALTER TYPE ... ADD VALUE to run OUTSIDE the normal
       transaction block (it cannot run inside the same
       transaction as other DDL/DML on modern Postgres) —
       done here via op.get_context().autocommit_block(),
       Alembic's documented pattern for this exact situation.
       IF NOT EXISTS makes this safe to re-run.
    2. Creates the health_reports table (Phase 1 of the
       Health Insights feature — see app/models/health_report.py's
       module docstring for why this has only two statuses,
       no raw file storage, and no separate uploaded/processing
       states).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Part 1: extend the existing interaction_type enum. Must run
    # outside the surrounding transaction — see module notes.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE interaction_type ADD VALUE IF NOT EXISTS 'health_report_analysis'")

    # Part 2: create the health_reports table.
    health_report_status = postgresql.ENUM(
        'awaiting_confirmation', 'confirmed',
        name='health_report_status',
    )
    health_report_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'health_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ai_interaction_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('report_label', sa.String(length=255), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM(
                'awaiting_confirmation', 'confirmed',
                name='health_report_status',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('extracted_markers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confirmed_markers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ai_interaction_id'], ['ai_interactions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_health_reports_user_id'), 'health_reports', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_health_reports_user_id'), table_name='health_reports')
    op.drop_table('health_reports')
    postgresql.ENUM(name='health_report_status').drop(op.get_bind(), checkfirst=True)
    # Note: Postgres does not support removing a value from an enum
    # type (ALTER TYPE ... DROP VALUE does not exist), so
    # 'health_report_analysis' cannot be cleanly removed from
    # interaction_type on downgrade. This is a known, accepted
    # asymmetry — same situation any enum-extending migration in
    # Postgres has.
