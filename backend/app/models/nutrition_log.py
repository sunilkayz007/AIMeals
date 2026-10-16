"""
=========================================================
AIMeals Backend
Nutrition Log Model

Responsibilities:
    - Define the nutrition_logs table schema
    - Define the MealType enum

Dependencies:
    - app.B_database.Base
    - app.models.user.User
    - app.models.recipe.Recipe (nullable FK)
    - app.models.food_image.FoodImage (nullable FK)

Notes:
    - recipe_id is NULLABLE and ON DELETE SET NULL:
      a log entry can exist from manual entry (no recipe)
      or from cooking a saved recipe (linked). If the
      recipe is later deleted, the log entry survives —
      food history should never be destroyed by an
      unrelated recipe deletion.
    - logged_at is separate from created_at: logged_at is
      the date this entry counts toward (user-controlled,
      e.g. logging a late-night snack against "today"),
      while created_at is when the row was actually
      inserted (system-controlled, for auditing).
    - UPDATED (soft meal-confirmation prompt feature):
      food_image_id is the same nullable/SET NULL pattern
      as recipe_id — a log entry can trace back to the
      food-image scan it came from, when logged via the
      "did you eat this?" flow instead of manual entry or
      a recipe.
    - portion_percentage (0-100, default 100.0) records how
      much of the recipe/scan was actually consumed. A log
      entry created from the full recipe/scan (the normal
      case, and every entry logged before this feature
      existed) is 100.0. calories/protein_g/carbs_g/fat_g on
      THIS row are already the SCALED values (e.g. 60% of a
      recipe's calories) — portion_percentage is stored
      alongside for display/audit purposes ("60% of Chilli
      Chicken"), not because the macros need to be
      recalculated from it again.

Example usage:
    from app.models.nutrition_log import NutritionLog, MealType

    log = NutritionLog(
        user_id=user.id,
        logged_at=date.today(),
        meal_type=MealType.LUNCH,
        food_name="Grilled Chicken Salad",
        calories=450,
        protein_g=35,
        carbs_g=20,
        fat_g=22,
    )
=========================================================
"""

import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Meal Type Enum
# =========================================================

class MealType(str, enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


# =========================================================
# Nutrition Log Model
# =========================================================

class NutritionLog(Base):
    """
    Represents a single logged food entry.

    Table: nutrition_logs
    """

    __tablename__ = "nutrition_logs"

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
    # Entry Details
    # ---------------------------------------------------

    logged_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    meal_type: Mapped[MealType] = mapped_column(
        Enum(MealType, name="meal_type"),
        nullable=False,
    )

    food_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ---------------------------------------------------
    # Macros (already scaled by portion_percentage, if < 100)
    # ---------------------------------------------------

    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)

    # Added 2026-08-06 — water contributed by this specific food
    # entry (scaled by portion_percentage, same as the macros
    # above), sourced from the recipe/scan's water_ml_per_serving
    # estimate. Defaults to 0.0 (not nullable) so SUM() across a
    # day never needs a null check, matching the calories/macros
    # pattern. A manual entry with no water estimate available
    # simply logs 0.0 here — it doesn't fabricate a number.
    water_ml: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Added alongside the Home screen's 6-card "Today at a glance"
    # redesign (Aug 2026) — fiber contributed by this specific food
    # entry, same scaled-by-portion_percentage / defaults-to-0.0 /
    # not-nullable pattern as water_ml above. A manual entry or a
    # source (recipe/scan) with no fiber estimate available simply
    # logs 0.0 here rather than fabricating a number.
    fiber_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Added alongside the 10-nutrient vitamin/mineral tracking
    # feature (Aug 2026) — a single JSONB dict holding all 10
    # values together (see app.core.micronutrients.MICRONUTRIENT_KEYS
    # for the exact key list), rather than 10 separate float columns
    # like fiber_g/water_ml got. Nullable, since a manual entry with
    # no estimate available simply has no micronutrient data at all
    # (treated as all-zeros by app.core.micronutrients.sanitize_micronutrients()
    # when read, not stored as literal zeros here).
    micronutrients: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # How much of the source recipe/scan this entry represents —
    # see module docstring. Default 100.0 = the whole thing.
    portion_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
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
        return f"<NutritionLog id={self.id} user_id={self.user_id} food={self.food_name}>"
