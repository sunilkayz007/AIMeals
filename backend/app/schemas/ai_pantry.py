"""
=========================================================
AIMeals Backend
AI Pantry Chef Schemas

Responsibilities:
    - Define the request shape for the Pantry Chef streaming
      endpoint

Notes:
    - No response schema — same as ai_recipe.py, the "result"
      event's shape is RecipeOut, serialized with
      .model_dump(mode="json") in the route.
    - UPDATED (fail-open-with-confirmation allergen design):
      confirm_allergen_override / warning_text_shown /
      recipe_preview_override / flagged_allergens_override
      mirror app.schemas.ai_recipe.RecipeGenerationRequest
      exactly — see that class's docstring for the full
      reasoning. Added so Pantry Chef reaches the same
      "Generate Anyway" flow as typed recipe generation
      instead of always failing closed on an allergen hit.
      All four default to safe values, so an existing client
      that doesn't send them behaves exactly as before.

Example usage:
    from app.schemas.ai_pantry import PantryChefRequest

    def suggest(payload: PantryChefRequest):
        ...
=========================================================
"""

from typing import List, Optional

from pydantic import BaseModel


# =========================================================
# Request Schema — Pantry Chef
# =========================================================

class PantryChefRequest(BaseModel):
    """
    Shape of the payload accepted by POST /ai/recipes/from-pantry.

    selected_ingredients: if provided, used exactly as given —
        the client has already let the user pick specific
        pantry items (and/or add extras). If omitted, the
        service auto-selects from the full pantry, prioritizing
        items expiring within 3 days.
    additional_preferences: any extra free-text request, e.g.
        "keep it vegetarian today" or "something quick".

    confirm_allergen_override / warning_text_shown /
    recipe_preview_override / flagged_allergens_override:
    same fail-open-with-confirmation fields as
    RecipeGenerationRequest — see that schema's docstring.
    """

    selected_ingredients: Optional[List[str]] = None
    additional_preferences: str = ""

    # When False (the default) and an allergen is detected,
    # the suggestion is rejected and NOT saved — the response
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
