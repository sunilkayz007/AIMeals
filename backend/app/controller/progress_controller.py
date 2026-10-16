"""
=========================================================
AIMeals Backend
Progress Controller

Responsibilities:
    - Orchestrate calls to ProgressService
    - Translate framework-agnostic service exceptions into
      HTTPException with correct status codes
    - Convert SQLAlchemy models into Pydantic response schemas

Dependencies:
    - app.services.progress_service.ProgressService
    - app.core.exceptions

Notes:
    - log_entry() maps DuplicateProgressEntryError -> 409,
      since the one-entry-per-user-per-day rule is a genuine
      conflict, not a validation error or a missing resource.
    - get_entry_for_date() returns None (not 404) — matching
      "no entry logged for this day" as a normal, expected
      state (e.g. a calendar view checking each day),
      consistent with get_recipe()/get_plan()'s pattern of
      letting the caller decide what None means for their case.
=========================================================
"""

import uuid
from datetime import date
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateProgressEntryError,
    NotProgressEntryOwnerError,
    ProgressEntryNotFoundError,
)
from app.schemas.progress import ProgressEntryCreate, ProgressEntryOut, ProgressEntryUpdate
from app.services.progress_service import ProgressService


# =========================================================
# Progress Controller
# =========================================================

class ProgressController:
    """
    Thin orchestration layer between API routes and ProgressService.
    """

    def __init__(self, db: Session):
        self.service = ProgressService(db)

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def log_entry(self, user_id: uuid.UUID, payload: ProgressEntryCreate) -> ProgressEntryOut:
        try:
            entry = self.service.log_entry(
                user_id=user_id,
                recorded_date=payload.recorded_date,
                weight_kg=payload.weight_kg,
                body_fat_percentage=payload.body_fat_percentage,
                waist_cm=payload.waist_cm,
                chest_cm=payload.chest_cm,
                hip_cm=payload.hip_cm,
                notes=payload.notes,
            )
        except DuplicateProgressEntryError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

        return ProgressEntryOut.model_validate(entry)

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_entry_for_date(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> Optional[ProgressEntryOut]:
        entry = self.service.get_entry_for_date(user_id, target_date)
        if entry is None:
            return None
        return ProgressEntryOut.model_validate(entry)

    def get_trend(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> List[ProgressEntryOut]:
        entries = self.service.get_trend(user_id, start_date, end_date)
        return [ProgressEntryOut.model_validate(e) for e in entries]

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update_entry(
        self,
        entry_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: ProgressEntryUpdate,
    ) -> ProgressEntryOut:
        fields = payload.model_dump(exclude_unset=True)

        try:
            entry = self.service.update_entry(entry_id, user_id, **fields)
        except ProgressEntryNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotProgressEntryOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )

        return ProgressEntryOut.model_validate(entry)

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete_entry(self, entry_id: uuid.UUID, user_id: uuid.UUID) -> None:
        try:
            self.service.delete_entry(entry_id, user_id)
        except ProgressEntryNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotProgressEntryOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )