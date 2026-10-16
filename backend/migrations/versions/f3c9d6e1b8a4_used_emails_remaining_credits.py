"""used emails remaining credits

Revision ID: f3c9d6e1b8a4
Revises: e2b7c4f9a1d3
Create Date: 2026-08-12

=========================================================
AIMeals Backend
Migration: Used Emails Remaining Credits

Purpose:
    Adds remaining_credits to used_emails, redesigning it from
    a simple "has this email signed up before" flag into a
    carrier of the actual unused credit balance at the moment
    of account deletion. On resignup with the same email, that
    balance is restored exactly — preventing farming (you can
    never gain credits by deleting) while being fair to a
    legitimate reason for deleting and recreating an account
    (you never lose credits you hadn't used either).
    server_default matches the normal Free-tier default, for
    the one pre-existing test row from before this redesign.
=========================================================
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3c9d6e1b8a4"
down_revision = "e2b7c4f9a1d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("used_emails")]

    if "remaining_credits" not in columns:
        op.add_column(
            "used_emails",
            sa.Column("remaining_credits", sa.Integer(), nullable=False, server_default="20"),
        )


def downgrade() -> None:
    op.drop_column("used_emails", "remaining_credits")