"""
=========================================================
AIMeals Backend
Progress Service

Responsibilities:
    - Orchestrate progress entry logging
    - Translate the DB's one-entry-per-user-per-day unique
      constraint into a clear, catchable business exception
      instead of a raw IntegrityError bubbling up
    - Enforce ownership on edits/deletes

Dependencies:
    - app.repositories.progress_entry_repository.ProgressEntryRepository
    - app.core.exceptions

Example usage:
    from app.services.progress_service import ProgressService

    service = ProgressService(db)
    service.log_entry(user.id, date.today(), weight_kg=74.5)
    trend = service.get_trend(user.id, start, end)
=========================================================
"""

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateProgressEntryError,
    NotProgressEntryOwnerError,
    ProgressEntryNotFoundError,
)
from app.models.progress_entry import ProgressEntry
from app.repositories.progress_entry_repository import ProgressEntryRepository


# =========================================================
# Progress Service
# =========================================================

class ProgressService:
    """
    Contains the business logic for progress entry logging.
    """

    def __init__(self, db: Session):
        self.db = db
        self.progress_repo = ProgressEntryRepository(db)

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def log_entry(
        self,
        user_id: uuid.UUID,
        recorded_date: date,
        weight_kg: Optional[float] = None,
        body_fat_percentage: Optional[float] = None,
        waist_cm: Optional[float] = None,
        chest_cm: Optional[float] = None,
        hip_cm: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> ProgressEntry:
        """
        Logs a progress entry for a specific date.

        Raises:
            DuplicateProgressEntryError: if the user already
                has an entry for this date. This is checked
                proactively (rather than letting the DB's
                unique constraint raise a raw IntegrityError),
                so the caller gets a clear, catchable business
                exception instead of a database-level error.
                To change an existing day's entry, use
                update_entry() instead.
        """
        existing = self.progress_repo.get_by_user_and_date(user_id, recorded_date)
        if existing is not None:
            raise DuplicateProgressEntryError(
                f"User already has a progress entry for {recorded_date}. "
                f"Use update_entry() to modify it instead."
            )

        return self.progress_repo.create(
            user_id=user_id,
            recorded_date=recorded_date,
            weight_kg=weight_kg,
            body_fat_percentage=body_fat_percentage,
            waist_cm=waist_cm,
            chest_cm=chest_cm,
            hip_cm=hip_cm,
            notes=notes,
        )

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_entry_for_date(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> Optional[ProgressEntry]:
        return self.progress_repo.get_by_user_and_date(user_id, target_date)

    def get_trend(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> List[ProgressEntry]:
        """
        Returns a user's progress entries in chronological
        order across a date range — the natural shape for
        plotting a trend chart.
        """
        return self.progress_repo.get_by_user(user_id, start_date=start_date, end_date=end_date)

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update_entry(self, entry_id: uuid.UUID, user_id: uuid.UUID, **fields) -> ProgressEntry:
        """
        Updates an existing entry, enforcing ownership. This
        is the correct method to call for "I already logged
        today but want to correct the number" — as opposed to
        log_entry(), which refuses to create a second entry
        for an already-logged date.

        Raises:
            ProgressEntryNotFoundError, NotProgressEntryOwnerError
        """
        entry = self._get_owned_entry_or_raise(entry_id, user_id)
        return self.progress_repo.update(entry, **fields)

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete_entry(self, entry_id: uuid.UUID, user_id: uuid.UUID) -> None:
        entry = self._get_owned_entry_or_raise(entry_id, user_id)
        self.progress_repo.delete(entry)

    # ---------------------------------------------------
    # Internal Helper
    # ---------------------------------------------------

    def _get_owned_entry_or_raise(
        self,
        entry_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ProgressEntry:
        entry = self.progress_repo.get_by_id(entry_id)

        if entry is None:
            raise ProgressEntryNotFoundError(f"No progress entry found with id {entry_id}.")

        if entry.user_id != user_id:
            raise NotProgressEntryOwnerError("This progress entry belongs to another user.")

        return entry