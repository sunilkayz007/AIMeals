"""
=========================================================
AIMeals Backend
AI Meal Plan Generation Schemas

Responsibilities:
    - Define the request shape for the streaming meal plan
      generation endpoint

Notes:
    - No response schema — the streamed "result" event's shape
      is MealPlanOut (from app.schemas.meal_plan), serialized
      via .model_dump(mode="json") in the route.

Example usage:
    from app.schemas.ai_meal_plan import MealPlanGenerationRequest

    def generate(payload: MealPlanGenerationRequest):
        ...
=========================================================
"""

from datetime import date
from typing import List

from pydantic import BaseModel, field_validator, model_validator

from app.models.nutrition_log import MealType


# =========================================================
# Request Schema — Generate Meal Plan
# =========================================================

class MealPlanGenerationRequest(BaseModel):
    """
    Shape of the payload accepted by POST /ai/meal-plans/generate.
    """

    title: str
    start_date: date
    end_date: date
    meal_types: List[MealType]
    preferences: str = ""

    @field_validator("title")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title cannot be blank.")
        return value.strip()

    @field_validator("meal_types")
    @classmethod
    def validate_not_empty(cls, value: List[MealType]) -> List[MealType]:
        if not value:
            raise ValueError("meal_types cannot be empty — request at least one meal type.")
        return value

    @model_validator(mode="after")
    def validate_date_range(self) -> "MealPlanGenerationRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date.")
        return self