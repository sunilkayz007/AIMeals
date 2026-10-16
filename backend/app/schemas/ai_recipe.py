"""
=========================================================
AIMeals Backend
AI Recipe Generation Schemas

Responsibilities:
    - Define the request shape for the streaming recipe
      generation endpoint

Notes:
    - No response schema here — the streamed "result" event's
      shape is RecipeOut (from app.schemas.recipe), serialized
      via .model_dump(mode="json") in the route so UUID/datetime
      fields become JSON-safe before being embedded in the SSE
      payload.
    - UPDATED (fail-open-with-confirmation allergen design):
      confirm_allergen_override and warning_text_shown support
      the "Generate Anyway" flow. Both default to safe values
      so every existing caller that doesn't know about this
      flow is completely unaffected — a request with neither
      field set behaves exactly as before (fails closed on
      allergen detection).
    - UPDATED AGAIN (fixing a real bug found in testing):
      recipe_preview_override and flagged_allergens_override
      let the client send back the EXACT recipe content it
      already received in the allergen-warning preview, rather
      than the "Generate Anyway" retry triggering an entirely
      NEW Claude call. Without this, two real problems occurred:
      (1) Claude might generate a DIFFERENT recipe on retry
      (still instructed to avoid the allergen) — the user could
      see a recipe with peanuts, click "Generate Anyway", and
      get back a completely different peanut-free recipe that
      correctly doesn't get flagged, which is confusing and not
      what they asked for; (2) the user would be charged credits
      TWICE for one recipe — once for the original blocked
      attempt (never refunded, since a real API cost was already
      incurred) and again for the regeneration. When these two
      fields are provided alongside confirm_allergen_override,
      AIService.generate_recipe() skips calling Claude and
      skips charging a credit entirely — it just saves the
      exact previously-generated content, flagged, with a
      consent record. See generate_recipe()'s docstring for
      the full branching logic.

Example usage:
    from app.schemas.ai_recipe import RecipeGenerationRequest

    def generate(payload: RecipeGenerationRequest):
        ...
=========================================================
"""

from typing import Optional

from pydantic import BaseModel, field_validator


# =========================================================
# Request Schema — Generate Recipe
# =========================================================

class RecipeGenerationRequest(BaseModel):
    """
    Shape of the payload accepted by POST /ai/recipes/generate.
    """

    request_description: str

    # When False (the default) and an allergen is detected,
    # the recipe is rejected and NOT saved — the response
    # includes a preview + which allergens were flagged, so
    # the client can offer the user a "Generate Anyway" choice.
    # When True, this same request is expected to be re-sent
    # after the user explicitly confirms, ALONG WITH
    # recipe_preview_override/flagged_allergens_override below
    # — see this class's docstring for why those two fields are
    # required for the override to behave correctly.
    confirm_allergen_override: bool = False

    # The EXACT warning text the client displayed to the user
    # when they clicked "Generate Anyway" — required to be
    # meaningful when confirm_allergen_override is True, since
    # it becomes part of the permanent consent record (proving
    # what was actually shown, not just that something was).
    # Optional/ignored when confirm_allergen_override is False.
    warning_text_shown: Optional[str] = None

    # The exact recipe content the client received in the
    # allergen-warning preview (title, description, instructions,
    # ingredients, servings, macros, closing_note — the same
    # shape as recipe_preview in the error event's data). When
    # provided alongside confirm_allergen_override=True, the
    # backend saves THIS content directly instead of calling
    # Claude again. Required for a correct override — see this
    # class's docstring.
    recipe_preview_override: Optional[dict] = None

    # The exact allergens that were flagged on the original
    # (blocked) attempt — sent back so the backend doesn't need
    # to re-run the safety checks against content it isn't
    # re-generating. Required alongside recipe_preview_override.
    flagged_allergens_override: Optional[list[str]] = None

    @field_validator("request_description")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_description cannot be blank.")
        return value.strip()