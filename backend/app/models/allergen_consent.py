"""
=========================================================
AIMeals Backend
Allergen Override Consent Model

Responsibilities:
    - Define the allergen_override_consents table schema —
      a permanent, immutable legal consent record created
      every time a user confirms "Generate Anyway" on a
      recipe that was flagged as containing one of their
      known allergens.

Dependencies:
    - app.B_database.Base
    - app.models.user.User (nullable FK)
    - app.models.recipe.Recipe (nullable FK)

Notes:
    - This is DELIBERATELY separate from the Recipe model's
      contains_allergen/flagged_allergens columns. Those
      columns answer "does this recipe contain an allergen"
      for display purposes (e.g. the red-fill warning in the
      app). This table answers "did the user see a specific
      warning and explicitly consent to it" — a legal
      question, not a display question. They serve different
      purposes and must not be conflated into one record.
    - Both foreign keys use ON DELETE SET NULL, not CASCADE.
      This record must survive the deletion of the user
      account or the recipe itself — that's the entire point
      of a liability record. The denormalized snapshot fields
      (user_email_snapshot, user_name_snapshot,
      recipe_title_snapshot) exist so the record remains
      meaningful even after such a deletion, when the FKs
      alone would otherwise point at nothing.
    - warning_text_shown captures the EXACT text the user saw
      at the moment they consented — not a reference to
      current UI copy, which could change later. This is the
      single most important field for a dispute: it proves
      what was actually displayed, not what the app currently
      displays.
    - No update/delete methods exist on this model's
      repository by design. This table is INSERT-ONLY. If
      that assumption ever needs to change, it should be a
      deliberate, discussed decision — not an accidental
      capability added while building something else.

Example usage:
    from app.models.allergen_consent import AllergenOverrideConsent

    consent = AllergenOverrideConsent(
        user_id=user.id,
        recipe_id=recipe.id,
        user_email_snapshot=user.email,
        user_name_snapshot=f"{user.first_name} {user.last_name}",
        recipe_title_snapshot=recipe.title,
        flagged_allergens=["peanuts", "shellfish"],
        warning_text_shown="This recipe contains peanuts, shellfish...",
    )
=========================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Allergen Override Consent Model
# =========================================================

class AllergenOverrideConsent(Base):
    """
    A permanent, insert-only legal consent record. Created
    exactly once, at the moment a user confirms "Generate
    Anyway" on an allergen-flagged recipe.

    Table: allergen_override_consents
    """

    __tablename__ = "allergen_override_consents"

    # ---------------------------------------------------
    # Primary Key — this IS the consent_id referenced
    # elsewhere (e.g. shown to the user, mirrored into the
    # JSON consent ledger).
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Foreign Keys (nullable — SET NULL, never CASCADE;
    # this record must outlive the user/recipe it references)
    # ---------------------------------------------------

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------
    # Denormalized Snapshots — survive user/recipe deletion
    # ---------------------------------------------------

    user_email_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    user_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    recipe_title_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)

    # ---------------------------------------------------
    # The Consent Itself
    # ---------------------------------------------------

    flagged_allergens: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

    # The EXACT text shown to the user at confirmation time —
    # not a reference to current UI copy. See module docstring.
    warning_text_shown: Mapped[str] = mapped_column(Text, nullable=False)

    # ---------------------------------------------------
    # Timestamp — when consent was given. No updated_at:
    # this record is never modified after creation.
    # ---------------------------------------------------

    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user = relationship("User")
    recipe = relationship("Recipe")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<AllergenOverrideConsent id={self.id} user_id={self.user_id} recipe_id={self.recipe_id}>"