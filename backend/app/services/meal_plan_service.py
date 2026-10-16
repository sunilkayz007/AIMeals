"""
=========================================================
AIMeals Backend
Meal Plan Service

Responsibilities:
    - Orchestrate meal plan and meal creation/management
    - Enforce ownership: a Meal's owner is its parent
      MealPlan's owner, since Meal has no direct user_id

Dependencies:
    - app.repositories.meal_plan_repository (both repos)
    - app.core.exceptions

Example usage:
    from app.services.meal_plan_service import MealPlanService

    service = MealPlanService(db)
    plan = service.create_plan(user.id, "Week of Aug 3", start, end)
    service.add_meal(plan.id, user.id, scheduled_date, MealType.DINNER, recipe_id=recipe.id)
=========================================================
"""

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import MealPlanNotFoundError, NotMealPlanOwnerError
from app.models.meal import Meal
from app.models.meal_plan import MealPlan
from app.models.nutrition_log import MealType
from app.repositories.meal_plan_repository import MealPlanRepository, MealRepository


# =========================================================
# Meal Plan Service
# =========================================================

class MealPlanService:
    """
    Contains the business logic for meal plan and meal
    management.
    """

    def __init__(self, db: Session):
        self.db = db
        self.plan_repo = MealPlanRepository(db)
        self.meal_repo = MealRepository(db)

    # ---------------------------------------------------
    # Plan — Create
    # ---------------------------------------------------

    def create_plan(
        self,
        user_id: uuid.UUID,
        title: str,
        start_date: date,
        end_date: date,
    ) -> MealPlan:
        return self.plan_repo.create(
            user_id=user_id,
            title=title,
            start_date=start_date,
            end_date=end_date,
        )

    # ---------------------------------------------------
    # Plan — Read
    # ---------------------------------------------------

    def get_user_plans(self, user_id: uuid.UUID) -> List[MealPlan]:
        return self.plan_repo.get_by_user(user_id)

    def get_plan(self, plan_id: uuid.UUID) -> Optional[MealPlan]:
        return self.plan_repo.get_by_id(plan_id)

    # ---------------------------------------------------
    # Plan — Delete
    # ---------------------------------------------------

    def delete_plan(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Deletes a plan (and, via cascade, all of its meals),
        enforcing ownership.

        Raises:
            MealPlanNotFoundError, NotMealPlanOwnerError
        """
        plan = self._get_owned_plan_or_raise(plan_id, user_id)
        self.plan_repo.delete(plan)

    # ---------------------------------------------------
    # Meal — Create
    # ---------------------------------------------------

    def add_meal(
        self,
        plan_id: uuid.UUID,
        user_id: uuid.UUID,
        scheduled_date: date,
        meal_type: MealType,
        recipe_id: Optional[uuid.UUID] = None,
    ) -> Meal:
        """
        Adds a meal to a plan. Enforces that the caller owns
        the parent plan — a meal cannot be added to someone
        else's plan.

        Raises:
            MealPlanNotFoundError, NotMealPlanOwnerError
        """
        self._get_owned_plan_or_raise(plan_id, user_id)

        return self.meal_repo.create(
            meal_plan_id=plan_id,
            scheduled_date=scheduled_date,
            meal_type=meal_type,
            recipe_id=recipe_id,
        )

    # ---------------------------------------------------
    # Meal — Read
    # ---------------------------------------------------

    def get_meals_in_plan(self, plan_id: uuid.UUID) -> List[Meal]:
        return self.meal_repo.get_by_meal_plan(plan_id)

    def get_meals_for_week(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> List[Meal]:
        """
        Returns a user's planned meals across ALL of their
        plans within a date range — this is the query a
        weekly calendar view would actually use, since a
        user's meals may span multiple overlapping plans.
        """
        return self.meal_repo.get_by_user_and_date_range(user_id, start_date, end_date)

    # ---------------------------------------------------
    # Meal — Delete
    # ---------------------------------------------------

    def remove_meal(self, meal_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Removes a single meal from its plan (without deleting
        the whole plan), enforcing ownership via the meal's
        parent plan.

        Raises:
            MealPlanNotFoundError: if the meal itself doesn't
                exist, or if its parent plan somehow doesn't
                (shouldn't normally happen given the FK).
            NotMealPlanOwnerError: if the parent plan belongs
                to someone else.
        """
        meal = self.meal_repo.get_by_id(meal_id)

        if meal is None:
            raise MealPlanNotFoundError(f"No meal found with id {meal_id}.")

        self._get_owned_plan_or_raise(meal.meal_plan_id, user_id)

        self.meal_repo.delete(meal)

    # ---------------------------------------------------
    # Internal Helper
    # ---------------------------------------------------

    def _get_owned_plan_or_raise(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> MealPlan:
        plan = self.plan_repo.get_by_id(plan_id)

        if plan is None:
            raise MealPlanNotFoundError(f"No meal plan found with id {plan_id}.")

        if plan.user_id != user_id:
            raise NotMealPlanOwnerError("This meal plan belongs to another user.")

        return plan