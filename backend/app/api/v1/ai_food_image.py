"""
=========================================================
AIMeals Backend
AI Food Image Analysis API Routes

Endpoints:
    POST /api/v1/ai/food-image/analyze                 - analyze a food photo, streamed via SSE
    POST /api/v1/ai/food-image/{image_id}/resolve        - resolve one or more flagged item ambiguities, plain JSON (NOT streamed)
    GET  /api/v1/ai/food-image/recent                    - the current user's most recent scans, plain JSON (NOT streamed, free)

Requires a valid access token (Authorization: Bearer <token>).

Response format — /analyze (text/event-stream):
    event: stage    data: {"stage": "checking_credits"}
    event: stage    data: {"stage": "analyzing_image"}
    event: stage    data: {"stage": "saving"}
    event: result   data: {...FoodImageOut fields, JSON-safe...}

    On failure, a single error event replaces the result event:
    event: error    data: {"error_type": "InappropriateImageError", "detail": "..."}

Response format — /resolve: a plain JSON FoodImageOut, NOT an
SSE stream — resolve_food_image_ambiguity() makes NO Claude
call (every alternative was already computed up front during
/analyze), so there's no multi-step pipeline to show progress
for.

Notes:
    - /analyze accepts multipart/form-data (an image file
      upload), like /ingredient-scan/identify — not JSON.
    - No image is ever saved to disk — bytes are read into
      memory, sent to Claude, then discarded.
    - Per-item detection: the result's `detected_foods` list has one
      entry per independently-detected food item. Any item
      whose confidence was low carries its own `alternatives`
      — check each item's `alternatives` array (not a single
      top-level ambiguity) to know what still needs resolving.
    - /resolve accepts MULTIPLE resolutions in one call — a
      list of {item_index, chosen_label} pairs, letting a
      client show every open question at once and submit all
      answers together, since each item's ambiguity is
      independent of every other item's.
    - /resolve is free — no credit cost.

Dependencies:
    - app.core.sse_streaming.stream_ai_progress
    - app.services.ai_service.AIService
    - app.schemas.food_image.FoodImageOut, ResolveAmbiguityRequest
    - app.core.dependencies.get_current_user
=========================================================
"""

import uuid

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    FoodImageAnalysisError,
    FoodImageNotFoundError,
    NotFoodImageOwnerError,
)
from app.core.sse_streaming import stream_ai_progress
from app.models.food_image import FoodImage
from app.models.user import User
from app.schemas.food_image import FoodImageOut, ResolveAmbiguityRequest
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


def _serialize_food_image(image: FoodImage) -> dict:
    return FoodImageOut.model_validate(image).model_dump(mode="json")


# =========================================================
# Analyze Food Image — Streamed via SSE
# =========================================================

@router.post("/food-image/analyze")
async def analyze_food_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Analyzes an uploaded photo, detecting every distinct food
    item independently. Streams progress stages, then a final
    result event with the created FoodImage analysis.

    If any item in the result's `detected_foods` list has a non-empty
    `alternatives`, that specific item is still ambiguous —
    show its alternatives to the user, then call
    POST /food-image/{image_id}/resolve with their choice(s).

    Returns an error event with error_type
    "InappropriateImageError" if the image isn't food or is
    otherwise unsuitable to analyze.
    """
    image_bytes = await image.read()
    media_type = image.content_type or "image/jpeg"

    service = AIService(db)

    return StreamingResponse(
        stream_ai_progress(
            service.analyze_food_image,
            serialize_result=_serialize_food_image,
            user_id=current_user.id,
            image_bytes=image_bytes,
            media_type=media_type,
            original_filename=image.filename or "upload.jpg",
        ),
        media_type="text/event-stream",
    )


# =========================================================
# Resolve Ambiguity — Plain JSON (not streamed, free, no Claude call)
# =========================================================

@router.post(
    "/food-image/{image_id}/resolve",
    response_model=FoodImageOut,
    status_code=status.HTTP_200_OK,
)
def resolve_ambiguity(
    image_id: uuid.UUID,
    payload: ResolveAmbiguityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FoodImageOut:
    """
    Resolves one or more of a PENDING analysis's independently-
    ambiguous items. Free — no credit cost, no Claude call.

    Returns 404 if no such analysis exists, 403 if it belongs
    to another user, 400 if it's not PENDING, an item_index is
    out of range, an item has no pending alternatives, or a
    chosen_label doesn't match any of that item's alternatives.
    """
    service = AIService(db)

    resolutions = [(r.item_index, r.chosen_label) for r in payload.resolutions]

    try:
        resolved = service.resolve_food_image_items(
            image_id=image_id,
            user_id=current_user.id,
            resolutions=resolutions,
        )
    except FoodImageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotFoodImageOwnerError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except FoodImageAnalysisError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return FoodImageOut.model_validate(resolved)

# =========================================================
# Recent Scans — Plain JSON (not streamed, free, no Claude call)
# =========================================================

@router.get(
    "/food-image/recent",
    response_model=List[FoodImageOut],
    status_code=status.HTTP_200_OK,
)
def get_recent_food_images(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[FoodImageOut]:
    """
    Returns the current user's most recent food-image scans
    (any status), most recent first. Free — no credit cost, no
    Claude call. Backs the "Recent scans" section shown on the
    Food Scan screen before a new scan is started.
    """
    service = AIService(db)
    images = service.get_recent_food_images(current_user.id, limit=limit)
    return [FoodImageOut.model_validate(image) for image in images]

