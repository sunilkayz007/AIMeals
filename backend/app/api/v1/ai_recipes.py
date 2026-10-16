"""
=========================================================
AIMeals Backend
AI Recipe Generation API Route

Endpoint:
    POST /api/v1/ai/recipes/generate   - generate a recipe from a free-text request, streamed via SSE

Requires a valid access token (Authorization: Bearer <token>).

Response format (text/event-stream):
    event: stage    data: {"stage": "checking_credits"}
    event: stage    data: {"stage": "generating"}
    event: stage    data: {"stage": "checking_safety"}
    event: stage    data: {"stage": "verifying_safety"}
    event: stage    data: {"stage": "saving"}
    event: result   data: {...RecipeOut fields, JSON-safe...}

    On failure, a single error event replaces the result event:
    event: error    data: {"error_type": "AllergenDetectedError", "detail": "..."}

    When an allergen is detected and confirm_allergen_override
    was NOT set, the error event ALSO includes recipe_preview
    and flagged_allergens (see AllergenDetectedError.sse_extra_data
    in core/exceptions.py) so the client can offer a "Generate
    Anyway" choice without anything having been saved yet:
    event: error    data: {"error_type": "AllergenDetectedError", "detail": "...", "recipe_preview": {...}, "flagged_allergens": [...]}

    To actually confirm the override, the client re-sends this
    same endpoint with confirm_allergen_override=true AND
    recipe_preview_override/flagged_allergens_override set to
    exactly what it received above — see
    AIService.generate_recipe()'s docstring for why sending the
    original content back (rather than letting the backend
    regenerate) is required for a correct override.

Notes:
    - Uses stream_ai_progress (discrete named STAGES), not
      stream_ai_text (live text chunks) — unlike chat, this
      returns one structured Recipe object, not long prose
      worth watching assemble word-by-word.
    - serialize_result converts the returned Recipe ORM object
      into RecipeOut, then .model_dump(mode="json") so UUID/
      datetime fields become JSON-safe before being embedded in
      the SSE payload (raw UUID/datetime objects aren't JSON-
      serializable by json.dumps).

Dependencies:
    - app.core.sse_streaming.stream_ai_progress
    - app.services.ai_service.AIService
    - app.schemas.recipe.RecipeOut
    - app.core.dependencies.get_current_user
=========================================================
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.core.sse_streaming import stream_ai_progress
from app.models.user import User
from app.models.recipe import Recipe
from app.schemas.ai_recipe import RecipeGenerationRequest
from app.schemas.recipe import RecipeOut
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


def _serialize_recipe(recipe: Recipe) -> dict:
    payload = RecipeOut.model_validate(recipe).model_dump(mode="json")
    # closing_note and consent_id are ephemeral (never persisted to
    # the DB), so they aren't part of RecipeOut/the Recipe model at
    # all. Read via getattr with a safe default and fold them into
    # this one response only.
    payload["closing_note"] = getattr(recipe, "closing_note", None)
    payload["consent_id"] = getattr(recipe, "consent_id", None)
    return payload


# =========================================================
# Generate Recipe — Streamed via SSE
# =========================================================

@router.post("/recipes/generate")
async def generate_recipe(
    payload: RecipeGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Generates a recipe from a free-text request (e.g. "high
    protein breakfast, no dairy"). Streams progress stages,
    then a final result event with the created recipe.

    Respects the user's allergies/dietary restrictions
    automatically, and runs both safety layers before saving —
    see AIService.generate_recipe()'s docstring for the full
    safety design, including the fail-open-with-confirmation
    flow driven by payload.confirm_allergen_override and the
    recipe_preview_override/flagged_allergens_override fields
    that make a confirmed override reuse the exact previously-
    generated content instead of calling Claude again.
    """
    service = AIService(db)

    return StreamingResponse(
        stream_ai_progress(
            service.generate_recipe,
            serialize_result=_serialize_recipe,
            user_id=current_user.id,
            request_description=payload.request_description,
            confirm_allergen_override=payload.confirm_allergen_override,
            warning_text_shown=payload.warning_text_shown,
            recipe_preview_override=payload.recipe_preview_override,
            flagged_allergens_override=payload.flagged_allergens_override,
        ),
        media_type="text/event-stream",
    )