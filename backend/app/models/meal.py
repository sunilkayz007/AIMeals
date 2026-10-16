"""
=========================================================
AIMeals Backend
Meal Model

Responsibilities:
    - Define the meals table schema

Dependencies:
    - app.B_database.Base
    - app.models.meal_plan.MealPlan
    - app.models.recipe.Recipe
    - app.models.nutrition_log.MealType (reused enum)

Notes:
    - Reuses the MealType enum from nutrition_log.py rather
      than defining a duplicate breakfast/lunch/dinner/snack
      enum — same concept, no reason to have two.
    - recipe_id is nullable: a planned meal slot could exist
      before a recipe has been chosen/generated for it yet.

Example usage:
    from app.models.meal import Meal
    from app.models.nutrition_log import MealType

    meal = Meal(
        meal_plan_id=plan.id,
        recipe_id=recipe.id,
        scheduled_date=date(2026, 8, 4),
        meal_type=MealType.DINNER,
    )
=========================================================
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base
from app.models.nutrition_log import MealType


# =========================================================
# Meal Model
# =========================================================

class Meal(Base):
    """
    Represents a single planned meal slot within a MealPlan.

    Table: meals
    """

    __tablename__ = "meals"

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

    meal_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meal_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recipe_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------
    # Scheduling
    # ---------------------------------------------------

    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    meal_type: Mapped[MealType] = mapped_column(
        Enum(MealType, name="meal_type"),
        nullable=False,
    )

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

    meal_plan = relationship("MealPlan", back_populates="meals")
    recipe = relationship("Recipe")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<Meal id={self.id} scheduled_date={self.scheduled_date} meal_type={self.meal_type}>"