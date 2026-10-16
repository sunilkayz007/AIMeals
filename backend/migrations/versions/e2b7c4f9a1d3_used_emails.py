"""used emails

Revision ID: e2b7c4f9a1d3
Revises: d8a3f5c2e9b7
Create Date: 2026-08-12

=========================================================
AIMeals Backend
Migration: Used Emails

Purpose:
    Adds used_emails, which tracks (via hash only) which
    email addresses have already claimed a Free-tier signup
    — deliberately NOT cleared by account deletion, since its
    purpose is preventing delete-and-resignup credit farming.
    See app/models/used_email.py for the full reasoning.
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e2b7c4f9a1d3"
down_revision = "d8a3f5c2e9b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "used_emails" not in inspector.get_table_names():
        op.create_table(
            "used_emails",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("email_hash", sa.String(255), nullable=False, unique=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_used_emails_email_hash", "used_emails", ["email_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_used_emails_email_hash", table_name="used_emails")
    op.drop_table("used_emails")