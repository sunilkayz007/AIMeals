"""
=========================================================
AIMeals Backend
Nutrition Log API Routes

Endpoints:
    POST   /api/v1/nutrition-logs                                       - log a meal manually
    POST   /api/v1/nutrition-logs/from-recipe                           - log a meal, macros auto-filled from a recipe (supports portion_percentage)
    POST   /api/v1/nutrition-logs/from-food-image                       - log a meal, macros auto-filled from a confirmed food-image scan (supports portion_percentage)
    GET    /api/v1/nutrition-logs/pending-confirmations                 - recent recipes/scans not yet logged or dismissed ("did you eat this?")
    POST   /api/v1/nutrition-logs/pending-confirmations/{type}/{id}/dismiss - dismiss one, so it stops being asked about
    GET    /api/v1/nutrition-logs/day/{target_date}                     - all logs for a single day
    GET    /api/v1/nutrition-logs/day/{target_date}/totals              - summed macros for a single day
    GET    /api/v1/nutrition-logs/range                                 - all logs in a date range
    PATCH  /api/v1/nutrition-logs/{log_id}                              - partial update (owner only)
    DELETE /api/v1/nutrition-logs/{log_id}                              - delete (owner only)

All endpoints require a valid access token (Authorization: Bearer <token>).

Dependencies:
    - app.controller.nutrition_log_controller.NutritionLogController
    - app.core.dependencies.get_current_user
    - app.B_database.get_db
=========================================================
"""

import uuid
from datetime import date
from typing import List, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.controller.nutrition_log_controller import NutritionLogController
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.nutrition_log import (
    DailyTotalsOut,
    NutritionLogCreate,
    NutritionLogFromFoodImageCreate,
    NutritionLogFromRecipeCreate,
    NutritionLogOut,
    NutritionLogUpdate,
    PendingConfirmationOut,
)

router = APIRouter(prefix="/api/v1/nutrition-logs", tags=["Nutrition Log"])


# =========================================================
# Log Meal — Manual Entry
# =========================================================

@router.post(
    "",
    response_model=NutritionLogOut,
    status_code=status.HTTP_201_CREATED,
)
def log_meal(
    payload: NutritionLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NutritionLogOut:
    """
    Logs a meal with manually-provided nutrition values.
    """
    controller = NutritionLogController(db)
    return controller.log_meal(current_user.id, payload)


# =========================================================
# Log Meal — From Recipe (auto-filled macros)
# =========================================================

@router.post(
    "/from-recipe",
    response_model=NutritionLogOut,
    status_code=status.HTTP_201_CREATED,
)
def log_meal_from_recipe(
    payload: NutritionLogFromRecipeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NutritionLogOut:
    """
    Logs a meal using a recipe's stored nutrition values,
    scaled by payload.portion_percentage (default 100 = the
    whole recipe), so the client doesn't need to re-send or
    compute macros itself.

    Returns 404 if no such recipe exists.
    """
    controller = NutritionLogController(db)
    return controller.log_meal_from_recipe(current_user.id, payload)


# =========================================================
# Log Meal — From Food Image Scan (auto-filled macros)
# =========================================================

@router.post(
    "/from-food-image",
    response_model=NutritionLogOut,
    status_code=status.HTTP_201_CREATED,
)
def log_meal_from_food_image(
    payload: NutritionLogFromFoodImageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NutritionLogOut:
    """
    Logs a meal using a food-image scan's computed totals,
    scaled by payload.portion_percentage.

    Returns 404 if no such scan exists, 403 if it belongs to
    another user, 409 if the scan still has unresolved
    ambiguous items (resolve those first via the food-image
    resolve endpoint before logging).
    """
    controller = NutritionLogController(db)
    return controller.log_meal_from_food_image(current_user.id, payload)


# =========================================================
# Pending Meal Confirmations ("did you eat this?")
# =========================================================

@router.get(
    "/pending-confirmations",
    response_model=List[PendingConfirmationOut],
    status_code=status.HTTP_200_OK,
)
def get_pending_confirmations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PendingConfirmationOut]:
    """
    Returns recent recipes/scans (last 48 hours) that haven't
    been logged or dismissed yet — the source list for the
    "did you eat this?" soft prompt.
    """
    controller = NutritionLogController(db)
    return controller.get_pending_confirmations(current_user.id)


@router.post(
    "/pending-confirmations/{source_type}/{source_id}/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
)
def dismiss_pending_confirmation(
    source_type: Literal["recipe", "food_image"],
    source_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Dismisses a pending confirmation (the user said "No" or
    skipped it) — it will not appear in
    GET /pending-confirmations again.
    """
    controller = NutritionLogController(db)
    controller.dismiss_pending_confirmation(current_user.id, source_type, source_id)


# =========================================================
# Get Logs For a Day
# =========================================================

@router.get(
    "/day/{target_date}",
    response_model=List[NutritionLogOut],
    status_code=status.HTTP_200_OK,
)
def get_logs_for_day(
    target_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[NutritionLogOut]:
    """
    Returns every log entry for the current user on a single date.
    """
    controller = NutritionLogController(db)
    return controller.get_logs_for_day(current_user.id, target_date)


# =========================================================
# Get Daily Totals
# =========================================================

@router.get(
    "/day/{target_date}/totals",
    response_model=DailyTotalsOut,
    status_code=status.HTTP_200_OK,
)
def get_daily_totals(
    target_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyTotalsOut:
    """
    Returns summed calories/protein/carbs/fat across all of
    the current user's log entries for a single day. Always
    returns real numbers (0, not null) if there are no entries.
    """
    controller = NutritionLogController(db)
    return controller.get_daily_totals(current_user.id, target_date)


# =========================================================
# Get Logs For a Date Range
# =========================================================

@router.get(
    "/range",
    response_model=List[NutritionLogOut],
    status_code=status.HTTP_200_OK,
)
def get_logs_for_range(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[NutritionLogOut]:
    """
    Returns every log entry for the current user within an
    inclusive date range.
    """
    controller = NutritionLogController(db)
    return controller.get_logs_for_range(current_user.id, start_date, end_date)


# =========================================================
# Update Log Entry
# =========================================================

@router.patch(
    "/{log_id}",
    response_model=NutritionLogOut,
    status_code=status.HTTP_200_OK,
)
def update_log(
    log_id: uuid.UUID,
    payload: NutritionLogUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NutritionLogOut:
    """
    Partially updates a log entry. Only fields included in
    the request body are changed.

    Returns 404 if no such log exists, 403 if it belongs to
    another user.
    """
    controller = NutritionLogController(db)
    return controller.update_log(log_id, current_user.id, payload)


# =========================================================
# Delete Log Entry
# =========================================================

@router.delete(
    "/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_log(
    log_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Deletes a log entry.

    Returns 404 if no such log exists, 403 if it belongs to
    another user.
    """
    controller = NutritionLogController(db)
    controller.delete_log(log_id, current_user.id)