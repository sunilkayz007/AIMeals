"""
=========================================================
AIMeals Backend
Meal Plan & Meal Repositories

Responsibilities:
    - Perform CRUD operations against the meal_plans and
      meals tables
    - Contains NO business logic

Dependencies:
    - app.models.meal_plan.MealPlan
    - app.models.meal.Meal

Notes:
    - Meal has no direct user_id column — a meal belongs to
      a meal_plan, which belongs to a user. MealRepository's
      get_by_user_and_date_range() joins through MealPlan to
      answer "what does this user have planned this week."
    - Deleting a MealPlan cascades to delete its Meal rows,
      via the model's cascade="all, delete-orphan" — this
      is enforced at the SQLAlchemy/application level, not
      the database level, so it only takes effect when a
      MealPlan is deleted through this repository (or any
      other path that loads it via the ORM), not via raw SQL.

Example usage:
    from app.repositories.meal_plan_repository import (
        MealPlanRepository, MealRepository
    )

    plan_repo = MealPlanRepository(db)
    plan = plan_repo.create(user.id, "Week of Aug 3", start_date, end_date)

    meal_repo = MealRepository(db)
    meal_repo.create(plan.id, scheduled_date, MealType.DINNER, recipe_id=recipe.id)
=========================================================
"""

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.meal import Meal
from app.models.meal_plan import MealPlan
from app.models.nutrition_log import MealType


# =========================================================
# Meal Plan Repository
# =========================================================

class MealPlanRepository:
    """
    Encapsulates all direct database access for the MealPlan model.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, plan_id: uuid.UUID) -> Optional[MealPlan]:
        return self.db.query(MealPlan).filter(MealPlan.id == plan_id).first()

    def get_by_user(self, user_id: uuid.UUID) -> List[MealPlan]:
        return (
            self.db.query(MealPlan)
            .filter(MealPlan.user_id == user_id)
            .order_by(MealPlan.start_date.desc())
            .all()
        )

    def create(
        self,
        user_id: uuid.UUID,
        title: str,
        start_date: date,
        end_date: date,
    ) -> MealPlan:
        new_plan = MealPlan(
            user_id=user_id,
            title=title,
            start_date=start_date,
            end_date=end_date,
        )

        self.db.add(new_plan)
        self.db.commit()
        self.db.refresh(new_plan)

        return new_plan

    def update(self, plan: MealPlan, **fields) -> MealPlan:
        for key, value in fields.items():
            setattr(plan, key, value)

        self.db.commit()
        self.db.refresh(plan)

        return plan

    def delete(self, plan: MealPlan) -> None:
        """
        Deletes a meal plan. Its Meal rows are deleted
        automatically via cascade="all, delete-orphan".
        """
        self.db.delete(plan)
        self.db.commit()


# =========================================================
# Meal Repository
# =========================================================

class MealRepository:
    """
    Encapsulates all direct database access for the Meal model.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, meal_id: uuid.UUID) -> Optional[Meal]:
        return self.db.query(Meal).filter(Meal.id == meal_id).first()

    def get_by_meal_plan(self, meal_plan_id: uuid.UUID) -> List[Meal]:
        return (
            self.db.query(Meal)
            .filter(Meal.meal_plan_id == meal_plan_id)
            .order_by(Meal.scheduled_date)
            .all()
        )

    def get_by_user_and_date_range(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> List[Meal]:
        """
        Returns all planned meals for a user within a date
        range, across all of their meal plans. Joins through
        MealPlan since Meal has no direct user_id column.
        """
        return (
            self.db.query(Meal)
            .join(MealPlan, Meal.meal_plan_id == MealPlan.id)
            .filter(
                MealPlan.user_id == user_id,
                Meal.scheduled_date >= start_date,
                Meal.scheduled_date <= end_date,
            )
            .order_by(Meal.scheduled_date)
            .all()
        )

    def create(
        self,
        meal_plan_id: uuid.UUID,
        scheduled_date: date,
        meal_type: MealType,
        recipe_id: Optional[uuid.UUID] = None,
    ) -> Meal:
        new_meal = Meal(
            meal_plan_id=meal_plan_id,
            recipe_id=recipe_id,
            scheduled_date=scheduled_date,
            meal_type=meal_type,
        )

        self.db.add(new_meal)
        self.db.commit()
        self.db.refresh(new_meal)

        return new_meal

    def update(self, meal: Meal, **fields) -> Meal:
        for key, value in fields.items():
            setattr(meal, key, value)

        self.db.commit()
        self.db.refresh(meal)

        return meal

    def delete(self, meal: Meal) -> None:
        self.db.delete(meal)
        self.db.commit()