"""
=========================================================
AIMeals Backend
AI Meal Nutrition Estimate Schemas

Responsibilities:
    - Define request/response shapes for the "Estimate with
      AI" feature on the manual meal-log form

Notes:
    - This is a NON-streamed, single request/response call —
      unlike recipe generation/food image analysis/health
      report analysis (which use stream_ai_progress's SSE
      pattern), this is a quick, cheap, single-turn text
      estimate, closer in shape to
      AIService.get_allergen_deep_insight() or
      confirm_health_report() than to the multi-stage
      generation flows. No progress stages are meaningful for
      a call this fast.
    - The response is NOT persisted anywhere by this endpoint
      — it only pre-fills the manual meal-log form client-side.
      The user still explicitly reviews and submits the actual
      log via the existing POST /nutrition-logs endpoint,
      exactly as if they'd typed the numbers in by hand.

Example usage:
    from app.schemas.ai_meal_estimate import (
        MealNutritionEstimateRequest,
        MealNutritionEstimateResponse,
    )
=========================================================
"""

from typing import Dict, Optional

from pydantic import BaseModel, field_validator


class MealNutritionEstimateRequest(BaseModel):
    """
    Shape of the payload accepted by
    POST /api/v1/ai/nutrition/estimate.
    """

    food_name: str
    # Optional extra context — e.g. "1 medium bowl", "2 slices",
    # "about 300g" — anything the user typed beyond the bare food
    # name that would help size the estimate. Free text, not a
    # structured quantity/unit pair, since manual entries don't
    # have the structured quantity/unit fields the ingredient-scan
    # flow does.
    quantity_description: Optional[str] = None

    @field_validator("food_name")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("food_name cannot be blank.")
        return value.strip()


class MealNutritionEstimateResponse(BaseModel):
    """
    Shape of the estimate returned to the client — matches the
    manual meal-log form's own field set exactly (calories
    through micronutrients), so the frontend can pre-fill the
    form directly from this response with no reshaping.
    """

    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    water_ml: float
    micronutrients: Dict[str, float]
