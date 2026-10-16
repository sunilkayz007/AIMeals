"""
=========================================================
AIMeals Backend
Meal Plan Model

Responsibilities:
    - Define the meal_plans table schema

Dependencies:
    - app.B_database.Base
    - app.models.user.User

Notes:
    - A MealPlan is a container (e.g. "Week of Aug 3").
      Individual planned meals live in the Meal model,
      each referencing back to a meal_plan_id.
    - This is distinct from NutritionLog: MealPlan/Meal
      represent PLANNED/FUTURE meals, NutritionLog
      represents ACTUALLY EATEN/PAST meals. Keeping these
      separate lets the AI coach later compare "planned
      vs actual" — a plan can exist without ever being
      eaten, and a log entry can exist without ever having
      been planned.

Example usage:
    from app.models.meal_plan import MealPlan

    plan = MealPlan(
        user_id=user.id,
        title="Week of Aug 3",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 9),
    )
=========================================================
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Meal Plan Model
# =========================================================

class MealPlan(Base):
    """
    Represents a container for a user's planned meals
    over a date range.

    Table: meal_plans
    """

    __tablename__ = "meal_plans"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Foreign Key
    # ---------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------
    # Plan Details
    # ---------------------------------------------------

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user = relationship("User")
    meals = relationship("Meal", back_populates="meal_plan", cascade="all, delete-orphan")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<MealPlan id={self.id} title={self.title}>"