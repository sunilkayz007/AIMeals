"""
=========================================================
AIMeals Backend
Progress Entry Repository

Responsibilities:
    - Perform CRUD operations against the progress_entries table
    - Contains NO business logic

Dependencies:
    - app.models.progress_entry.ProgressEntry

Notes:
    - get_by_user_and_date returns a single Optional entry
      (not a list), unlike NutritionLog's equivalent method —
      this reflects the DB-enforced one-entry-per-user-per-day
      constraint on this table. Useful for "has the user
      already logged today" checks before showing a log form.

Example usage:
    from app.repositories.progress_entry_repository import ProgressEntryRepository

    repo = ProgressEntryRepository(db)
    trend = repo.get_by_user(user.id, start_date=thirty_days_ago, end_date=today)
=========================================================
"""

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.progress_entry import ProgressEntry


# =========================================================
# Progress Entry Repository
# =========================================================

class ProgressEntryRepository:
    """
    Encapsulates all direct database access for the ProgressEntry model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_id(self, entry_id: uuid.UUID) -> Optional[ProgressEntry]:
        return self.db.query(ProgressEntry).filter(ProgressEntry.id == entry_id).first()

    def get_by_user(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[ProgressEntry]:
        """
        Returns a user's progress entries, optionally filtered
        to a date range, ordered oldest-to-newest (natural
        order for plotting a trend line).
        """
        query = self.db.query(ProgressEntry).filter(ProgressEntry.user_id == user_id)

        if start_date is not None:
            query = query.filter(ProgressEntry.recorded_date >= start_date)
        if end_date is not None:
            query = query.filter(ProgressEntry.recorded_date <= end_date)

        return query.order_by(ProgressEntry.recorded_date.asc()).all()

    def get_by_user_and_date(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> Optional[ProgressEntry]:
        """
        Returns a user's single progress entry for a specific
        date, or None if they haven't logged that day. Returns
        a single entry (not a list) since the DB enforces one
        entry per user per day.
        """
        return (
            self.db.query(ProgressEntry)
            .filter(
                ProgressEntry.user_id == user_id,
                ProgressEntry.recorded_date == target_date,
            )
            .first()
        )

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
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
        new_entry = ProgressEntry(
            user_id=user_id,
            recorded_date=recorded_date,
            weight_kg=weight_kg,
            body_fat_percentage=body_fat_percentage,
            waist_cm=waist_cm,
            chest_cm=chest_cm,
            hip_cm=hip_cm,
            notes=notes,
        )

        self.db.add(new_entry)
        self.db.commit()
        self.db.refresh(new_entry)

        return new_entry

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update(self, entry: ProgressEntry, **fields) -> ProgressEntry:
        for key, value in fields.items():
            setattr(entry, key, value)

        self.db.commit()
        self.db.refresh(entry)

        return entry

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete(self, entry: ProgressEntry) -> None:
        self.db.delete(entry)
        self.db.commit()