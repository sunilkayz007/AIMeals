"""allergy facts and allergen insight caches

Revision ID: b7e2f9a4d3c6
Revises: c4f7a92e6b18
Create Date: 2026-08-06

=========================================================
AIMeals Backend
Migration: Allergy general facts + allergen insight caches

Purpose:
    Backs two new Allergies-screen features:
      1. "Things you might not know" — allergy_general_facts,
         one row per user, refreshed on a time/allergy-change
         basis (see AIService.get_allergy_general_facts()).
      2. "About your allergies" tap-through — allergen_insights
         (one row per MASTER allergen, shared across all users)
         + user_allergen_deep_unlocks (tracks which users have
         paid a credit to unlock which allergen's deep insight,
         so re-opening already-unlocked content is free).

ASSUMPTION FLAGGED: this migration assumes the existing master
allergen table is named "allergies" with a UUID primary key
"id" — inferred from AllergyRepository/Allergy model usage
elsewhere in the codebase (not directly visible in this
session's export). Verify before running if unsure.
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "b7e2f9a4d3c6"
down_revision = "c4f7a92e6b18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------
    # allergy_general_facts
    # ---------------------------------------------------
    op.create_table(
        "allergy_general_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("facts", postgresql.JSONB(), nullable=False),
        sa.Column("allergy_signature", sa.String(length=500), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_allergy_general_facts_user_id", "allergy_general_facts", ["user_id"])
    op.create_unique_constraint(
        "uq_allergy_general_facts_user_id", "allergy_general_facts", ["user_id"]
    )

    # ---------------------------------------------------
    # allergen_insights
    # ---------------------------------------------------
    op.create_table(
        "allergen_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "allergy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("allergies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("short_insight_text", sa.Text(), nullable=False),
        sa.Column(
            "short_generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deep_insight_text", sa.Text(), nullable=True),
        sa.Column("deep_generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_allergen_insights_allergy_id", "allergen_insights", ["allergy_id"])
    op.create_unique_constraint(
        "uq_allergen_insights_allergy_id", "allergen_insights", ["allergy_id"]
    )

    # ---------------------------------------------------
    # user_allergen_deep_unlocks
    # ---------------------------------------------------
    op.create_table(
        "user_allergen_deep_unlocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "allergy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("allergies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "unlocked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_user_allergen_deep_unlocks_user_id", "user_allergen_deep_unlocks", ["user_id"]
    )
    op.create_index(
        "ix_user_allergen_deep_unlocks_allergy_id", "user_allergen_deep_unlocks", ["allergy_id"]
    )
    op.create_unique_constraint(
        "uq_user_allergen_deep_unlocks_user_allergy",
        "user_allergen_deep_unlocks",
        ["user_id", "allergy_id"],
    )


def downgrade() -> None:
    op.drop_table("user_allergen_deep_unlocks")
    op.drop_constraint("uq_allergen_insights_allergy_id", "allergen_insights", type_="unique")
    op.drop_index("ix_allergen_insights_allergy_id", table_name="allergen_insights")
    op.drop_table("allergen_insights")
    op.drop_constraint(
        "uq_allergy_general_facts_user_id", "allergy_general_facts", type_="unique"
    )
    op.drop_index("ix_allergy_general_facts_user_id", table_name="allergy_general_facts")
    op.drop_table("allergy_general_facts")