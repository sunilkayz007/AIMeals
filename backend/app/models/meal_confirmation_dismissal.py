"""
=========================================================
AIMeals Backend
Meal Confirmation Dismissal Model

Responsibilities:
    - Define the meal_confirmation_dismissals table schema —
      records when a user explicitly dismisses (says "No" to,
      or skips) a soft "did you eat this?" prompt about a
      specific recipe or food-image scan, so that item stops
      being asked about again.

Dependencies:
    - app.B_database.Base
    - app.models.user.User
    - app.models.recipe.Recipe (nullable FK)
    - app.models.food_image.FoodImage (nullable FK)

Notes:
    - Exactly ONE of recipe_id/food_image_id is set per row,
      never both — this is NOT enforced at the database level
      (no CHECK constraint), it's trusted to the service layer.
      Same dual-nullable-FK pattern already used elsewhere in
      this codebase (see AllergenOverrideConsent) for "this
      row is about one of two possible source types."
    - Both FKs use ON DELETE SET NULL, not CASCADE — if the
      underlying recipe or food image is later deleted, the
      dismissal record survives as a historical fact rather
      than silently disappearing (though in practice, once
      dismissed, nothing queries against a deleted source
      again anyway — this is just consistent with the FK
      pattern used everywhere else in the app).
    - No update method needed — a dismissal is a one-time
      fact, never edited. Only created and read.

Example usage:
    from app.models.meal_confirmation_dismissal import MealConfirmationDismissal

    dismissal = MealConfirmationDismissal(
        user_id=user.id,
        recipe_id=recipe.id,
    )
=========================================================
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Meal Confirmation Dismissal Model
# =========================================================

class MealConfirmationDismissal(Base):
    """
    Records that a user dismissed a "did you eat this?" prompt
    for a specific recipe or food-image scan.

    Table: meal_confirmation_dismissals
    """

    __tablename__ = "meal_confirmation_dismissals"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Foreign Keys
    # ---------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recipe_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    food_image_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("food_images.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------
    # Timestamp
    # ---------------------------------------------------

    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user = relationship("User")
    recipe = relationship("Recipe")
    food_image = relationship("FoodImage")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<MealConfirmationDismissal id={self.id} user_id={self.user_id} "
            f"recipe_id={self.recipe_id} food_image_id={self.food_image_id}>"
        )