"""
=========================================================
AIMeals Backend
Nutrition Log Schemas

Responsibilities:
    - Define request/response shapes for meal logging

Notes:
    - Three create schemas, matching three separate service
      methods: NutritionLogCreate for manual entries (macros
      typed by hand), NutritionLogFromRecipeCreate for
      recipe-based entries (macros auto-filled server-side
      from the recipe), and NutritionLogFromFoodImageCreate
      for scan-based entries (macros auto-filled from a
      confirmed FoodImage's totals).
    - UPDATED (soft meal-confirmation prompt feature):
      NutritionLogFromRecipeCreate and
      NutritionLogFromFoodImageCreate both accept
      portion_percentage (0-100, default 100.0) — how much of
      the recipe/scan was actually consumed. The service layer
      scales the source's macros by this before saving; the
      client never computes/sends the scaled numbers itself.
    - PendingConfirmationOut / the pending-confirmations
      endpoint is what powers the "did you eat the Chilli
      Chicken you made earlier?" soft prompt — see
      NutritionLogService.get_pending_confirmations() for the
      full selection logic (recent, unlogged, undismissed
      recipes/scans).
    - UPDATED (Home screen 6-card redesign, Aug 2026):
      fiber_g added throughout, same optional/defaults-to-0.0
      treatment as water_ml — manual entries can type it in,
      recipe/food-image entries get it auto-filled and scaled
      server-side same as the other macros.

Example usage:
    from app.schemas.nutrition_log import NutritionLogCreate, NutritionLogOut

    def log_meal(payload: NutritionLogCreate):
        ...
=========================================================
"""

import uuid
from datetime import date, datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.nutrition_log import MealType


# =========================================================
# Request Schema — Manual Log Entry
# =========================================================

class NutritionLogCreate(BaseModel):
    """
    Shape of the payload accepted by POST /nutrition-logs.

    recipe_id is optional here too — a manual entry can still
    reference a recipe for record-keeping without pulling its
    macros automatically. Use POST /nutrition-logs/from-recipe
    instead when you want the macros auto-filled.
    """

    logged_at: date
    meal_type: MealType
    food_name: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 0.0
    water_ml: float = 0.0
    micronutrients: Optional[Dict[str, float]] = None
    recipe_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

    @field_validator("food_name")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("food_name cannot be blank.")
        return value.strip()


# =========================================================
# Request Schema — Log From Recipe
# =========================================================

class NutritionLogFromRecipeCreate(BaseModel):
    """
    Shape of the payload accepted by POST /nutrition-logs/from-recipe.

    No macro fields here — they're pulled server-side from
    the recipe's own stored nutrition data, then scaled by
    portion_percentage, so the client never re-types (or could
    tamper with) numbers that already exist on the recipe.
    """

    logged_at: date
    meal_type: MealType
    recipe_id: uuid.UUID
    portion_percentage: float = Field(default=100.0, ge=0, le=100)
    notes: Optional[str] = None


# =========================================================
# Request Schema — Log From Food Image Scan
# =========================================================

class NutritionLogFromFoodImageCreate(BaseModel):
    """
    Shape of the payload accepted by POST /nutrition-logs/from-food-image.

    No macro fields here either — pulled server-side from the
    FoodImage's own computed totals, then scaled by
    portion_percentage. The FoodImage must be CONFIRMED (not
    PENDING) — an unresolved ambiguous scan doesn't have final
    totals yet, so logging from it is rejected until the user
    resolves it via the existing free resolve endpoint.
    """

    logged_at: date
    meal_type: MealType
    food_image_id: uuid.UUID
    portion_percentage: float = Field(default=100.0, ge=0, le=100)
    notes: Optional[str] = None


# =========================================================
# Request Schema — Update Log Entry
# =========================================================

class NutritionLogUpdate(BaseModel):
    """
    Shape of the payload accepted by PATCH /nutrition-logs/{log_id}.

    All fields optional. Like other Update schemas in this
    project, NutritionLogService.update_log() does not filter
    unset fields itself — the controller uses
    payload.model_dump(exclude_unset=True).
    """

    logged_at: Optional[date] = None
    meal_type: Optional[MealType] = None
    food_name: Optional[str] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    water_ml: Optional[float] = None
    micronutrients: Optional[Dict[str, float]] = None
    recipe_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

    @field_validator("food_name")
    @classmethod
    def validate_not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("food_name cannot be blank.")
        return value.strip() if value is not None else value


# =========================================================
# Response Schema — Log Entry
# =========================================================

class NutritionLogOut(BaseModel):
    """
    Shape of nutrition log data returned to the client.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    recipe_id: Optional[uuid.UUID] = None
    food_image_id: Optional[uuid.UUID] = None
    logged_at: date
    meal_type: MealType
    food_name: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 0.0
    water_ml: float = 0.0
    micronutrients: Optional[Dict[str, float]] = None
    portion_percentage: float = 100.0
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# Response Schema — Daily Totals
# =========================================================

class DailyTotalsOut(BaseModel):
    """
    Shape returned by GET /nutrition-logs/day/{target_date}/totals.

    Always has real numeric values (0, not null) even for a
    day with zero entries — matches
    NutritionLogService.get_daily_totals()'s own guarantee, so
    the client can always safely use this in arithmetic or
    display it directly without a null check.
    """

    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    water_ml: float
    micronutrients: Dict[str, float]
    entry_count: int


# =========================================================
# Response Schema — Pending Meal Confirmation
# =========================================================

class PendingConfirmationOut(BaseModel):
    """
    Shape of a single item in the "did you eat this?" list —
    an AI-generated-or-manual recipe, or a confirmed food-image
    scan, from the last 48 hours, not yet logged and not yet
    dismissed. See
    NutritionLogService.get_pending_confirmations() for the
    exact selection logic.

    source_type distinguishes which endpoint to call next:
    "recipe" -> POST /nutrition-logs/from-recipe with this id
    as recipe_id; "food_image" -> POST /nutrition-logs/from-food-image
    with this id as food_image_id.
    """

    source_type: Literal["recipe", "food_image"]
    source_id: uuid.UUID
    title: str
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    created_at: datetime
