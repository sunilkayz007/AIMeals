"""
=========================================================
AIMeals Backend
AI Ingredient Scan API Routes

Endpoints:
    POST /api/v1/ai/ingredient-scan/identify                        - step 1: identify ingredients from a photo, streamed via SSE
    POST /api/v1/ai/ingredient-scan/{scan_id}/generate-recipe        - step 2: generate a recipe from the confirmed/corrected scan, streamed via SSE
    GET  /api/v1/ai/ingredient-scan/recent                          - the current user's most recent scans, plain JSON (NOT streamed, free)

Requires a valid access token (Authorization: Bearer <token>).

Response format — step 1 (text/event-stream):
    event: stage    data: {"stage": "checking_credits"}
    event: stage    data: {"stage": "analyzing_image"}
    event: stage    data: {"stage": "saving"}
    event: result   data: {...IngredientScanOut fields, JSON-safe...}

Response format — step 2 (text/event-stream):
    event: stage    data: {"stage": "checking_credits"}
    event: stage    data: {"stage": "generating"}
    event: stage    data: {"stage": "checking_safety"}
    event: stage    data: {"stage": "verifying_safety"}
    event: stage    data: {"stage": "saving"}
    event: result   data: {...RecipeOut fields, JSON-safe...}

    On failure (either endpoint), a single error event replaces
    the result event:
    event: error    data: {"error_type": "...", "detail": "..."}

    Step 2 supports the same fail-open-with-confirmation
    allergen flow as /ai/recipes/generate (see that route's
    docstring for the full shape). When an allergen is
    detected and confirm_allergen_override was NOT set, the
    error event ALSO includes recipe_preview and
    flagged_allergens so the client can offer a "Generate
    Anyway" choice without anything having been saved yet:
    event: error    data: {"error_type": "AllergenDetectedError", "detail": "...", "recipe_preview": {...}, "flagged_allergens": [...]}

    To confirm the override, the client re-sends step 2 with
    confirm_allergen_override=true AND
    recipe_preview_override/flagged_allergens_override set to
    exactly what it received above — see
    AIService.generate_recipe()'s docstring for why sending
    the original content back (rather than letting the
    backend regenerate) is required for a correct override.

Notes:
    - Step 1 accepts multipart/form-data (an actual image file
      upload), NOT JSON — this is the one AI route that isn't a
      plain JSON body, since it's a real file upload.
    - Step 2's route is separate from step 1's — two distinct
      Claude calls, two distinct credit charges, with a
      user-review step in between (the user sees step 1's
      identified ingredients and can correct them before
      calling step 2).
    - No image is ever saved to disk for either step — bytes
      are read into memory, sent to Claude, then discarded.

Dependencies:
    - app.core.sse_streaming.stream_ai_progress
    - app.services.ai_service.AIService
    - app.schemas.ingredient_scan.IngredientScanOut
    - app.schemas.recipe.RecipeOut
    - app.core.dependencies.get_current_user
=========================================================
"""

import uuid

from typing import List

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.core.sse_streaming import stream_ai_progress
from app.models.ingredient_scan import IngredientScan
from app.models.recipe import Recipe
from app.models.user import User
from app.schemas.ingredient_scan import GenerateRecipeFromScanRequest, IngredientScanOut
from app.schemas.recipe import RecipeOut
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


def _serialize_scan(scan: IngredientScan) -> dict:
    return IngredientScanOut.model_validate(scan).model_dump(mode="json")


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
# Step 1: Identify Ingredients From Photo — Streamed via SSE
# =========================================================

@router.post("/ingredient-scan/identify")
async def identify_ingredients(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Identifies raw ingredients visible in an uploaded photo.
    Streams progress stages, then a final result event with
    the created (PENDING) IngredientScan — review/correct the
    ingredients client-side, then call step 2.
    """
    image_bytes = await image.read()
    media_type = image.content_type or "image/jpeg"

    service = AIService(db)

    return StreamingResponse(
        stream_ai_progress(
            service.identify_ingredients_from_image,
            serialize_result=_serialize_scan,
            user_id=current_user.id,
            image_bytes=image_bytes,
            media_type=media_type,
        ),
        media_type="text/event-stream",
    )


# =========================================================
# Step 2: Generate Recipe From Scan — Streamed via SSE
# =========================================================

@router.post("/ingredient-scan/{scan_id}/generate-recipe")
async def generate_recipe_from_scan(
    scan_id: uuid.UUID,
    payload: GenerateRecipeFromScanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Generates a recipe from a previously-identified ingredient
    scan, applying any corrections the user made. Streams
    progress stages, then a final result event with the
    created recipe.

    Returns an error event with error_type
    "IngredientScanNotFoundError" or "NotIngredientScanOwnerError"
    if the scan doesn't exist or belongs to another user.
    """
    service = AIService(db)

    return StreamingResponse(
        stream_ai_progress(
            service.generate_recipe_from_scan,
            serialize_result=_serialize_recipe,
            scan_id=scan_id,
            user_id=current_user.id,
            corrected_ingredient_names=payload.corrected_ingredient_names,
            additional_preferences=payload.additional_preferences,
            confirm_allergen_override=payload.confirm_allergen_override,
            warning_text_shown=payload.warning_text_shown,
            recipe_preview_override=payload.recipe_preview_override,
            flagged_allergens_override=payload.flagged_allergens_override,
        ),
        media_type="text/event-stream",
    )

# =========================================================
# Recent Scans — Plain JSON (not streamed, free, no Claude call)
# =========================================================

@router.get("/ingredient-scan/recent", response_model=List[IngredientScanOut])
def get_recent_ingredient_scans(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[IngredientScanOut]:
    """
    Returns the current user's most recent ingredient scans
    (any status), most recent first. Free — no credit cost, no
    Claude call. Backs the "Recent scans" section shown on the
    Ingredient Scan screen before a new scan is started. Scans
    are swept ~24h after creation by the TTL cleanup job, so
    this naturally only ever shows same-day activity.
    """
    service = AIService(db)
    scans = service.get_recent_ingredient_scans(current_user.id, limit=limit)
    return [IngredientScanOut.model_validate(scan) for scan in scans]
