"""
=========================================================
AIMeals Backend
Progress Schemas

Responsibilities:
    - Define request/response shapes for weight/measurement
      progress entries

Example usage:
    from app.schemas.progress import ProgressEntryCreate, ProgressEntryOut

    def log_entry(payload: ProgressEntryCreate):
        ...
=========================================================
"""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# =========================================================
# Request Schema — Log Progress Entry
# =========================================================

class ProgressEntryCreate(BaseModel):
    """
    Shape of the payload accepted by POST /progress.

    Raises DuplicateProgressEntryError (-> 409) if the user
    already has an entry for recorded_date — use
    PATCH /progress/{entry_id} to correct an existing day's
    entry instead of trying to log it twice.
    """

    recorded_date: date
    weight_kg: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    waist_cm: Optional[float] = None
    chest_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    notes: Optional[str] = None


# =========================================================
# Request Schema — Update Progress Entry
# =========================================================

class ProgressEntryUpdate(BaseModel):
    """
    Shape of the payload accepted by PATCH /progress/{entry_id}.

    All fields optional. Like other Update schemas in this
    project, ProgressService.update_entry() does not filter
    unset fields itself — the controller uses
    payload.model_dump(exclude_unset=True).
    """

    recorded_date: Optional[date] = None
    weight_kg: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    waist_cm: Optional[float] = None
    chest_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    notes: Optional[str] = None


# =========================================================
# Response Schema — Progress Entry
# =========================================================

class ProgressEntryOut(BaseModel):
    """
    Shape of progress entry data returned to the client.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    recorded_date: date
    weight_kg: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    waist_cm: Optional[float] = None
    chest_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)