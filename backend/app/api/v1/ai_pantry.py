"""
=========================================================
AIMeals Backend
AI Pantry Chef API Route

Endpoint:
    POST /api/v1/ai/recipes/from-pantry   - suggest a recipe from the user's pantry, streamed via SSE

Requires a valid access token (Authorization: Bearer <token>).

Response format: identical shape to /ai/recipes/generate (see
that route's docstring) — same stages, same result shape,
since suggest_recipe_from_pantry() is a thin wrapper around
generate_recipe() and inherits its exact behavior, safety
layers, and progress stages with zero duplicated logic. This
now includes the fail-open-with-confirmation allergen flow:
PantryChefRequest accepts the same confirm_allergen_override /
warning_text_shown / recipe_preview_override /
flagged_allergens_override fields as RecipeGenerationRequest,
so an allergen hit here can offer "Generate Anyway" too,
instead of always failing closed.

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
from app.models.recipe import Recipe
from app.models.user import User
from app.schemas.ai_pantry import PantryChefRequest
from app.schemas.recipe import RecipeOut
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


def _serialize_recipe(recipe: Recipe) -> dict:
    payload = RecipeOut.model_validate(recipe).model_dump(mode="json")
    # closing_note is ephemeral (never persisted to the DB — see
    # AIService.generate_recipe()'s comment on why), so it isn't
    # part of RecipeOut/the Recipe model at all. Read it via
    # getattr with a safe default and fold it into this one
    # response only.
    payload["closing_note"] = getattr(recipe, "closing_note", None)
    return payload


# =========================================================
# Pantry Chef — Streamed via SSE
# =========================================================

@router.post("/recipes/from-pantry")
async def suggest_recipe_from_pantry(
    payload: PantryChefRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Suggests a recipe built primarily from the user's pantry,
    prioritizing items expiring soon when no specific
    ingredients are selected. Streams progress stages, then a
    final result event with the created recipe.

    Returns a RecipeGenerationError (as an "error" SSE event)
    if the pantry is empty and no ingredients were selected.
    """
    service = AIService(db)

    return StreamingResponse(
        stream_ai_progress(
            service.suggest_recipe_from_pantry,
            serialize_result=_serialize_recipe,
            user_id=current_user.id,
            selected_ingredients=payload.selected_ingredients,
            additional_preferences=payload.additional_preferences,
            confirm_allergen_override=payload.confirm_allergen_override,
            warning_text_shown=payload.warning_text_shown,
            recipe_preview_override=payload.recipe_preview_override,
            flagged_allergens_override=payload.flagged_allergens_override,
        ),
        media_type="text/event-stream",
    )