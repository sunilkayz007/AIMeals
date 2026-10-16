"""
=========================================================
AIMeals Backend
Meal Plan Schemas

Responsibilities:
    - Define request/response shapes for meal plans and
      the individual meals within them

Notes:
    - No Update schemas — MealPlanService has no
      update_plan()/update_meal() methods, only create/read/
      delete for both. Not inventing update logic here that
      doesn't exist in the service layer.
    - MealCreate has no direct user_id — ownership is
      enforced through the parent MealPlan, matching
      MealPlanService's own design (Meal has no direct
      user_id column at all).

Example usage:
    from app.schemas.meal_plan import MealPlanCreate, MealPlanOut

    def create_plan(payload: MealPlanCreate):
        ...
=========================================================
"""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.nutrition_log import MealType


# =========================================================
# Request Schema — Create Meal Plan
# =========================================================

class MealPlanCreate(BaseModel):
    """
    Shape of the payload accepted by POST /meal-plans.
    """

    title: str
    start_date: date
    end_date: date

    @field_validator("title")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title cannot be blank.")
        return value.strip()

    @model_validator(mode="after")
    def validate_date_range(self) -> "MealPlanCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date.")
        return self


# =========================================================
# Response Schema — Meal Plan
# =========================================================

class MealPlanOut(BaseModel):
    """
    Shape of meal plan data returned to the client.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    start_date: date
    end_date: date
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# Request Schema — Add Meal to Plan
# =========================================================

class MealCreate(BaseModel):
    """
    Shape of the payload accepted by POST /meal-plans/{plan_id}/meals.

    recipe_id is optional — a planned meal slot can exist
    before a recipe has been chosen/generated for it yet.
    """

    scheduled_date: date
    meal_type: MealType
    recipe_id: Optional[uuid.UUID] = None


# =========================================================
# Response Schema — Meal
# =========================================================

class MealOut(BaseModel):
    """
    Shape of meal data returned to the client.
    """

    id: uuid.UUID
    meal_plan_id: uuid.UUID
    recipe_id: Optional[uuid.UUID] = None
    scheduled_date: date
    meal_type: MealType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)