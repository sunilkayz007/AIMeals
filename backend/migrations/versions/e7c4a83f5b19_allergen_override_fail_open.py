"""allergen override fail-open with consent record

Revision ID: e7c4a83f5b19
Revises: d3f8a29b1c47
Create Date: 2026-08-04

=========================================================
AIMeals Backend
Migration: Allergen override fail-open + consent record

Purpose:
    Supports the fail-open-with-confirmation redesign of
    Recipe Generation's allergen safety check (previously
    fail-closed only — an allergen match discarded the
    recipe entirely, no override possible).

    Adds to `recipes`:
        - contains_allergen (bool, default False) — DISPLAY
          flag only, drives the red-fill warning in the app.
        - flagged_allergens (JSONB, nullable) — which
          allergen(s) triggered the flag, for that same
          display purpose.

    Creates `allergen_override_consents` — a permanent,
    insert-only legal consent record, DELIBERATELY separate
    from the two columns above. Written exactly once, when a
    user confirms "Generate Anyway." Captures a snapshot of
    the user/recipe (surviving later deletion of either, via
    ON DELETE SET NULL rather than CASCADE) and the EXACT
    warning text shown at that moment. See
    app/models/allergen_consent.py's docstring for the full
    reasoning on why this is a separate table rather than
    just more columns on `recipes`.

    Existing recipes rows get contains_allergen=False,
    flagged_allergens=NULL (safe defaults — nothing about
    previously-saved recipes changes retroactively; this
    entire flow only applies going forward).
=========================================================
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e7c4a83f5b19"
down_revision = "d3f8a29b1c47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------
    # recipes: add display-only allergen flag columns
    # ---------------------------------------------------
    op.add_column(
        "recipes",
        sa.Column(
            "contains_allergen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "recipes",
        sa.Column(
            "flagged_allergens",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # ---------------------------------------------------
    # allergen_override_consents: new, insert-only table
    # ---------------------------------------------------
    op.create_table(
        "allergen_override_consents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("user_email_snapshot", sa.String(length=255), nullable=False),
        sa.Column("user_name_snapshot", sa.String(length=255), nullable=False),
        sa.Column("recipe_title_snapshot", sa.String(length=255), nullable=False),
        sa.Column(
            "flagged_allergens",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("warning_text_shown", sa.Text(), nullable=False),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_allergen_override_consents_user_id",
        "allergen_override_consents",
        ["user_id"],
    )
    op.create_index(
        "ix_allergen_override_consents_recipe_id",
        "allergen_override_consents",
        ["recipe_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_allergen_override_consents_recipe_id",
        table_name="allergen_override_consents",
    )
    op.drop_index(
        "ix_allergen_override_consents_user_id",
        table_name="allergen_override_consents",
    )
    op.drop_table("allergen_override_consents")

    op.drop_column("recipes", "flagged_allergens")
    op.drop_column("recipes", "contains_allergen")