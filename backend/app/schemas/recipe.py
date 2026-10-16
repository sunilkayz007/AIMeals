"""
=========================================================
AIMeals Backend
Recipe Schemas

Responsibilities:
    - Define request/response shapes for recipe data

Notes:
    - RecipeCreate deliberately has no is_ai_generated field —
      recipes created through this endpoint are always
      manually authored by the user. AI-generated recipes are
      created internally by AIService.generate_recipe() and
      its callers, not through this CRUD endpoint.
    - RecipeCreate/RecipeUpdate also have no created_by_user_id
      field — that's set server-side from the authenticated
      user, never trusted from the client.
    - RecipeCreate/RecipeUpdate also have no
      contains_allergen/flagged_allergens fields — these are
      set server-side ONLY by AIService.generate_recipe()'s
      fail-open-with-confirmation flow, never accepted directly
      from a client request. A manually-created recipe via
      POST /recipes always has contains_allergen=False (the
      model's default) — there's no allergen-checking pipeline
      on the manual CRUD path, only on AI generation.
    - contains_allergen/flagged_allergens on RecipeOut are
      DISPLAY fields only (e.g. driving the red-fill warning
      in the app) — see app/models/recipe.py's docstring for
      why this is deliberately separate from the actual legal
      consent record (AllergenOverrideConsent).
    - fiber_g_per_serving added throughout alongside the Home
      screen's 6-card redesign (Aug 2026), same optional/
      Claude-estimate treatment as water_ml_per_serving.

Example usage:
    from app.schemas.recipe import RecipeCreate, RecipeOut

    def create_recipe(payload: RecipeCreate):
        ...
=========================================================
"""

import uuid
from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, field_validator


# =========================================================
# Request Schema — Create Recipe
# =========================================================

class RecipeCreate(BaseModel):
    """
    Shape of the payload accepted by POST /recipes.
    """

    title: str
    instructions: str
    ingredients: str
    description: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    servings: int = 1
    calories_per_serving: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g_per_serving: Optional[float] = None
    water_ml_per_serving: Optional[float] = None
    micronutrients: Optional[Dict[str, float]] = None

    @field_validator("title", "instructions", "ingredients")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot be blank.")
        return value.strip()


# =========================================================
# Request Schema — Update Recipe
# =========================================================

class RecipeUpdate(BaseModel):
    """
    Shape of the payload accepted by PATCH /recipes/{recipe_id}.

    All fields optional. Like PantryItemUpdate,
    RecipeService.update_recipe() does not filter unset
    fields itself — the controller uses
    payload.model_dump(exclude_unset=True) so an omitted
    field is left untouched, not overwritten with null.
    """

    title: Optional[str] = None
    instructions: Optional[str] = None
    ingredients: Optional[str] = None
    description: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    servings: Optional[int] = None
    calories_per_serving: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g_per_serving: Optional[float] = None
    water_ml_per_serving: Optional[float] = None
    micronutrients: Optional[Dict[str, float]] = None

    @field_validator("title", "instructions", "ingredients")
    @classmethod
    def validate_not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("This field cannot be blank.")
        return value.strip() if value is not None else value


# =========================================================
# Response Schema — Recipe
# =========================================================

class RecipeOut(BaseModel):
    """
    Shape of recipe data returned to the client.

    created_by_user_id is None for system/curated recipes —
    the client can use that to distinguish "shared recipe" vs
    "a specific user's recipe" without a separate flag.
    """

    id: uuid.UUID
    created_by_user_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    instructions: str
    ingredients: str
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    servings: int
    calories_per_serving: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g_per_serving: Optional[float] = None
    water_ml_per_serving: Optional[float] = None
    micronutrients: Optional[Dict[str, float]] = None
    contains_allergen: bool = False
    flagged_allergens: Optional[list[str]] = None
    is_ai_generated: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
