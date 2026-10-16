"""
=========================================================
AIMeals Backend
AI Meal Plan Generation API Route

Endpoints:
    POST /api/v1/ai/meal-plans/generate            - generate a complete meal plan, streamed via SSE
    GET  /api/v1/ai/meal-plans/{plan_id}/meals      - meals for a plan, generating any due chunks first

Requires a valid access token (Authorization: Bearer <token>).

Response format for /generate (text/event-stream):
    event: stage    data: {"stage": "checking_credits"}
    event: stage    data: {"stage": "generating"}
    event: stage    data: {"stage": "checking_safety"}
    event: stage    data: {"stage": "verifying_safety"}
    event: stage    data: {"stage": "saving"}
    event: result   data: {...MealPlanOut fields, JSON-safe...}

    On failure, a single error event replaces the result event:
    event: error    data: {"error_type": "AllergenDetectedError", "detail": "..."}

Notes:
    - A plan generates in CHUNKS, not all at once (see
      AIService.generate_meal_plan()'s docstring for the full
      reasoning — short version: a single Claude call can't
      reliably produce a whole week's worth of complete
      recipes without truncating). /generate only creates the
      plan and its chunk schedule, then generates chunk 0
      synchronously — that's what this SSE stream reports
      progress for. Every LATER chunk generates lazily, pulled
      by GET .../meals below, the next time the plan's meals
      are fetched after that chunk's scheduled date arrives.
    - GET .../meals deliberately returns the SAME response
      shape (List[MealOut]) as the plain CRUD endpoint at
      GET /api/v1/meal-plans/{plan_id}/meals — this route just
      also generates any due-but-ungenerated chunks first. The
      CRUD route stays pure read-only, matching its own
      documented "no generation logic here" boundary; this AI
      route is where that boundary's counterpart lives.
    - If a due chunk can't generate (e.g. out of credits), it
      silently stays pending — no error, no partial content,
      just fewer meals in the returned list than the full plan
      will eventually have. See
      AIService.sync_due_meal_plan_chunks()'s docstring.

Dependencies:
    - app.core.sse_streaming.stream_ai_progress
    - app.services.ai_service.AIService
    - app.schemas.meal_plan.MealPlanOut / MealOut
    - app.core.dependencies.get_current_user
=========================================================
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.core.sse_streaming import stream_ai_progress
from app.models.meal_plan import MealPlan
from app.models.user import User
from app.schemas.ai_meal_plan import MealPlanGenerationRequest
from app.schemas.meal_plan import MealOut, MealPlanOut
from app.schemas.meal_plan_chunk import MealPlanChunkOut
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


def _serialize_meal_plan(plan: MealPlan) -> dict:
    return MealPlanOut.model_validate(plan).model_dump(mode="json")


# =========================================================
# Generate Meal Plan — Streamed via SSE
# =========================================================

@router.post("/meal-plans/generate")
async def generate_meal_plan(
    payload: MealPlanGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Creates a meal plan and generates its first chunk (see
    module notes above). Streams progress stages for that
    first chunk, then a final result event with the created
    plan container.

    Note: this returns the MealPlan container only — its
    meals (chunk 0's, generated already; later chunks',
    generated lazily) are fetched via
    GET /api/v1/ai/meal-plans/{plan_id}/meals.
    """
    service = AIService(db)

    return StreamingResponse(
        stream_ai_progress(
            service.generate_meal_plan,
            serialize_result=_serialize_meal_plan,
            user_id=current_user.id,
            title=payload.title,
            start_date=payload.start_date,
            end_date=payload.end_date,
            meal_types=payload.meal_types,
            preferences=payload.preferences,
        ),
        media_type="text/event-stream",
    )


# =========================================================
# Get Meals — Generates Any Due Chunks First
# =========================================================

@router.get("/meal-plans/{plan_id}/meals", response_model=List[MealOut])
def get_meals_syncing_due_chunks(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MealOut]:
    """
    Returns every meal scheduled within a plan, generating any
    chunks that are due but haven't generated yet first (see
    module notes above). Not streamed — chunk generation, if
    any happens, completes synchronously within this request;
    the response is a plain meal list either way, same shape
    as the CRUD endpoint.

    Returns 404 if no such plan exists, 403 if it belongs to
    another user.
    """
    service = AIService(db)

    plan = service.meal_plan_repo.get_by_id(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No meal plan found with id {plan_id}.")
    if plan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This meal plan belongs to another user.")

    meals = service.sync_due_meal_plan_chunks(plan_id, current_user.id)
    return [MealOut.model_validate(m) for m in meals]


# =========================================================
# Get Chunk Schedule/Status
# =========================================================

@router.get("/meal-plans/{plan_id}/chunks", response_model=List[MealPlanChunkOut])
def get_chunk_status(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MealPlanChunkOut]:
    """
    Returns the plan's chunk schedule — which date ranges are
    still PENDING (not generated yet), COMPLETED, or FAILED.
    Read-only, does NOT trigger generation of anything (that
    only happens via GET .../meals above) — this is purely so
    the frontend can render "not generated yet" for a date
    range instead of just silently showing no meals there with
    no explanation.

    Returns 404 if no such plan exists, 403 if it belongs to
    another user.
    """
    service = AIService(db)

    plan = service.meal_plan_repo.get_by_id(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No meal plan found with id {plan_id}.")
    if plan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This meal plan belongs to another user.")

    chunks = service.meal_plan_chunk_repo.get_by_plan(plan_id)
    return [MealPlanChunkOut.model_validate(c) for c in chunks]