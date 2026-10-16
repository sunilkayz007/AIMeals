"""
=========================================================
AIMeals Backend
Ingredient Scan Schemas

Responsibilities:
    - Define response shape for IngredientScan
    - Define the request shape for step 2 of the flow
      (generate a recipe from a confirmed/corrected scan)

Example usage:
    from app.schemas.ingredient_scan import IngredientScanOut

    def get_scan(scan: IngredientScan) -> IngredientScanOut:
        ...
=========================================================
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.ingredient_scan import IngredientScanStatus


# =========================================================
# Response Schema — Single Identified Ingredient
# =========================================================

class IdentifiedIngredientOut(BaseModel):
    """
    One entry in IngredientScan.ingredients (a JSONB list, not
    its own table) — {"name", "confidence_score",
    "confidence_note", "alternatives", "quantity", "unit"}.

    confidence_score: 0.0-1.0, Claude's own stated confidence.
    alternatives: other plausible names, populated only when
        confidence_score is below ~0.85 — pick from these (or
        supply your own) via corrected_ingredient_names on the
        generate-recipe step, no separate resolve endpoint needed.
    quantity/unit: structured (not free text), so this maps
        directly onto PantryItem.quantity/unit for future
        pantry integration.

    All defensively clamped/defaulted server-side (see
    AIService._parse_ingredient_identification_json) — never
    trust raw model-generated numbers/lists without a sanity check.
    """

    name: str
    confidence_score: Optional[float] = None
    confidence_note: Optional[str] = None
    alternatives: List[str] = []
    quantity: Optional[float] = None
    unit: Optional[str] = None


# =========================================================
# Response Schema — Ingredient Scan
# =========================================================

class IngredientScanOut(BaseModel):
    """
    Shape of ingredient scan data returned to the client.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    ingredients: List[IdentifiedIngredientOut]
    status: IngredientScanStatus
    ai_interaction_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# Request Schema — Generate Recipe From Scan (step 2)
# =========================================================

class GenerateRecipeFromScanRequest(BaseModel):
    """
    Shape of the payload accepted by
    POST /ai/ingredient-scan/{scan_id}/generate-recipe.

    corrected_ingredient_names: if provided, REPLACES the
        scan's identified ingredients entirely (the user fixed
        a misidentified item or removed one that wasn't
        actually there). If omitted (None), the originally
        identified ingredients are used as-is.
    additional_preferences: any extra free-text request, e.g.
        "make it vegetarian".

    confirm_allergen_override / warning_text_shown /
    recipe_preview_override / flagged_allergens_override:
    same fail-open-with-confirmation fields as
    app.schemas.ai_recipe.RecipeGenerationRequest — see that
    schema's docstring. Added so a scan-based recipe reaches
    the same "Generate Anyway" flow as typed recipe generation
    instead of always failing closed on an allergen hit. All
    four default to safe values, so an existing client that
    doesn't send them behaves exactly as before.
    """

    corrected_ingredient_names: Optional[List[str]] = None
    additional_preferences: str = ""

    # When False (the default) and an allergen is detected,
    # the recipe is rejected and NOT saved — the response
    # includes a preview + which allergens were flagged, so
    # the client can offer the user a "Generate Anyway" choice.
    confirm_allergen_override: bool = False

    # The EXACT warning text the client displayed to the user
    # when they clicked "Generate Anyway" — becomes part of the
    # permanent consent record. Optional/ignored when
    # confirm_allergen_override is False.
    warning_text_shown: Optional[str] = None

    # The exact recipe content the client received in the
    # allergen-warning preview. When provided alongside
    # confirm_allergen_override=True, the backend saves THIS
    # content directly instead of calling Claude again — see
    # AIService.generate_recipe()'s docstring for why this is
    # required for a correct override (avoids a different
    # recipe on retry and a double credit charge).
    recipe_preview_override: Optional[dict] = None

    # The exact allergens flagged on the original (blocked)
    # attempt. Required alongside recipe_preview_override.
    flagged_allergens_override: Optional[list[str]] = None