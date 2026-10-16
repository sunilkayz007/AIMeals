"""add ingredient interaction types to enum

Revision ID: a21f358b28ad
Revises: 82d7a9afc23f
Create Date: 2026-07-29

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "a21f358b28ad"
down_revision = "82d7a9afc23f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside the same
    # transaction as anything that uses the new value, and
    # this project's Alembic setup runs migrations
    # transactionally by default. autocommit_block() forces
    # this statement outside that transaction.
    #
    # NOTE: SQLAlchemy's Enum(InteractionType, ...) column
    # stores the Python enum's NAME (e.g. "CHAT"), not its
    # .value (e.g. "chat") — confirmed by inspecting the live
    # DB, which shows 'CHAT', 'RECIPE_GENERATION', etc. So the
    # new values added here must match that same uppercase
    # naming convention, not the lowercase snake_case .value.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE interaction_type ADD VALUE IF NOT EXISTS 'INGREDIENT_IMAGE_IDENTIFY'"
        )
        op.execute(
            "ALTER TYPE interaction_type ADD VALUE IF NOT EXISTS 'INGREDIENT_PHOTO_RECIPE'"
        )


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE. Removing an
    # enum value safely requires rebuilding the type (create
    # new type, migrate every column using it, drop the old
    # type) and rewriting any existing rows using the value
    # being removed. Deliberately left as a no-op rather than
    # a fake reversible migration — do this by hand if the
    # feature is ever fully rolled back.
    pass