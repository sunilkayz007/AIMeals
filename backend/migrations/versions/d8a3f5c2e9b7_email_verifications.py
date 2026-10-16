"""email verifications

Revision ID: d8a3f5c2e9b7
Revises: c6f9b2e4a8d1
Create Date: 2026-08-11

=========================================================
AIMeals Backend
Migration: Email Verifications

Purpose:
    Adds email_verifications, which holds short-lived OTP
    records for OTP-based signup — see AuthService's
    request_signup_otp() / verify_signup_otp() for the flow.
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d8a3f5c2e9b7"
down_revision = "c6f9b2e4a8d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "email_verifications" not in inspector.get_table_names():
        op.create_table(
            "email_verifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("otp_hash", sa.String(255), nullable=False),
            sa.Column("first_name", sa.String(100), nullable=False),
            sa.Column("last_name", sa.String(100), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_email_verifications_email", "email_verifications", ["email"])


def downgrade() -> None:
    op.drop_index("ix_email_verifications_email", table_name="email_verifications")
    op.drop_table("email_verifications")