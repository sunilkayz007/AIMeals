"""
=========================================================
AIMeals Backend
Progress API Routes

Endpoints:
    POST   /api/v1/progress                     - log a progress entry for a date
    GET    /api/v1/progress/day/{target_date}     - the entry for a single date (null if none)
    GET    /api/v1/progress/trend                 - entries in chronological order across a date range
    PATCH  /api/v1/progress/{entry_id}             - correct an existing entry (owner only)
    DELETE /api/v1/progress/{entry_id}             - delete an entry (owner only)

All endpoints require a valid access token (Authorization: Bearer <token>).

Notes:
    - POST returns 409 if an entry already exists for that
      date — use PATCH to correct an existing day's entry
      instead of logging it twice.

Dependencies:
    - app.controller.progress_controller.ProgressController
    - app.core.dependencies.get_current_user
    - app.B_database.get_db
=========================================================
"""

import uuid
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.controller.progress_controller import ProgressController
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.progress import ProgressEntryCreate, ProgressEntryOut, ProgressEntryUpdate

router = APIRouter(prefix="/api/v1/progress", tags=["Progress"])


# =========================================================
# Log Progress Entry
# =========================================================

@router.post(
    "",
    response_model=ProgressEntryOut,
    status_code=status.HTTP_201_CREATED,
)
def log_entry(
    payload: ProgressEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressEntryOut:
    """
    Logs a progress entry for a specific date.

    Returns 409 if the user already has an entry for that
    date — use PATCH /progress/{entry_id} instead to correct it.
    """
    controller = ProgressController(db)
    return controller.log_entry(current_user.id, payload)


# =========================================================
# Get Entry For a Date
# =========================================================

@router.get(
    "/day/{target_date}",
    response_model=ProgressEntryOut | None,
    status_code=status.HTTP_200_OK,
)
def get_entry_for_date(
    target_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressEntryOut | None:
    """
    Returns the current user's progress entry for a single
    date, or null if none was logged that day (a normal state,
    not an error).
    """
    controller = ProgressController(db)
    return controller.get_entry_for_date(current_user.id, target_date)


# =========================================================
# Get Trend
# =========================================================

@router.get(
    "/trend",
    response_model=List[ProgressEntryOut],
    status_code=status.HTTP_200_OK,
)
def get_trend(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ProgressEntryOut]:
    """
    Returns the current user's progress entries in
    chronological order across a date range — the shape a
    trend chart would consume directly.
    """
    controller = ProgressController(db)
    return controller.get_trend(current_user.id, start_date, end_date)


# =========================================================
# Update Entry
# =========================================================

@router.patch(
    "/{entry_id}",
    response_model=ProgressEntryOut,
    status_code=status.HTTP_200_OK,
)
def update_entry(
    entry_id: uuid.UUID,
    payload: ProgressEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressEntryOut:
    """
    Corrects an existing progress entry. Only fields included
    in the request body are changed.

    Returns 404 if no such entry exists, 403 if it belongs to
    another user.
    """
    controller = ProgressController(db)
    return controller.update_entry(entry_id, current_user.id, payload)


# =========================================================
# Delete Entry
# =========================================================

@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Deletes a progress entry.

    Returns 404 if no such entry exists, 403 if it belongs to
    another user.
    """
    controller = ProgressController(db)
    controller.delete_entry(entry_id, current_user.id)