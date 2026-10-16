"""
=========================================================
AIMeals Backend
Meal Plan Controller

Responsibilities:
    - Orchestrate calls to MealPlanService
    - Translate framework-agnostic service exceptions into
      HTTPException with correct status codes
    - Convert SQLAlchemy models into Pydantic response schemas

Dependencies:
    - app.services.meal_plan_service.MealPlanService
    - app.core.exceptions

Notes:
    - get_plan() returns None (not 404) — the ROUTE decides
      whether that becomes a 404, same pattern as
      recipe_controller.get_recipe().
    - add_meal()/remove_meal() both enforce ownership through
      the parent MealPlan, matching MealPlanService's design
      (Meal has no direct user_id column).
=========================================================
"""

import uuid
from datetime import date
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import MealPlanNotFoundError, NotMealPlanOwnerError
from app.schemas.meal_plan import MealCreate, MealOut, MealPlanCreate, MealPlanOut
from app.services.meal_plan_service import MealPlanService


# =========================================================
# Meal Plan Controller
# =========================================================

class MealPlanController:
    """
    Thin orchestration layer between API routes and MealPlanService.
    """

    def __init__(self, db: Session):
        self.service = MealPlanService(db)

    # ---------------------------------------------------
    # Plan — Create
    # ---------------------------------------------------

    def create_plan(self, user_id: uuid.UUID, payload: MealPlanCreate) -> MealPlanOut:
        plan = self.service.create_plan(
            user_id=user_id,
            title=payload.title,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        return MealPlanOut.model_validate(plan)

    # ---------------------------------------------------
    # Plan — Read
    # ---------------------------------------------------

    def get_user_plans(self, user_id: uuid.UUID) -> List[MealPlanOut]:
        plans = self.service.get_user_plans(user_id)
        return [MealPlanOut.model_validate(p) for p in plans]

    def get_plan(self, plan_id: uuid.UUID) -> Optional[MealPlanOut]:
        plan = self.service.get_plan(plan_id)
        if plan is None:
            return None
        return MealPlanOut.model_validate(plan)

    # ---------------------------------------------------
    # Plan — Delete
    # ---------------------------------------------------

    def delete_plan(self, plan_id: uuid.UUID, user_id: uuid.UUID) -> None:
        try:
            self.service.delete_plan(plan_id, user_id)
        except MealPlanNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotMealPlanOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )

    # ---------------------------------------------------
    # Meal — Create
    # ---------------------------------------------------

    def add_meal(
        self,
        plan_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: MealCreate,
    ) -> MealOut:
        try:
            meal = self.service.add_meal(
                plan_id=plan_id,
                user_id=user_id,
                scheduled_date=payload.scheduled_date,
                meal_type=payload.meal_type,
                recipe_id=payload.recipe_id,
            )
        except MealPlanNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotMealPlanOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )

        return MealOut.model_validate(meal)

    # ---------------------------------------------------
    # Meal — Read
    # ---------------------------------------------------

    def get_meals_in_plan(self, plan_id: uuid.UUID) -> List[MealOut]:
        meals = self.service.get_meals_in_plan(plan_id)
        return [MealOut.model_validate(m) for m in meals]

    def get_meals_for_week(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> List[MealOut]:
        meals = self.service.get_meals_for_week(user_id, start_date, end_date)
        return [MealOut.model_validate(m) for m in meals]

    # ---------------------------------------------------
    # Meal — Delete
    # ---------------------------------------------------

    def remove_meal(self, meal_id: uuid.UUID, user_id: uuid.UUID) -> None:
        try:
            self.service.remove_meal(meal_id, user_id)
        except MealPlanNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotMealPlanOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )