"""
=========================================================
AIMeals Backend
Water Log Schemas

Responsibilities:
    - Define request/response shapes for water logging and
      the combined daily water summary (manual + food-derived)

Example usage:
    from app.schemas.water_log import WaterLogCreate, WaterDaySummaryOut
=========================================================
"""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# =========================================================
# Request Schema — Manual Water Log
# =========================================================

class WaterLogCreate(BaseModel):
    """Shape of the payload accepted by POST /water-logs."""

    logged_at: date
    amount_ml: float = Field(gt=0)


# =========================================================
# Response Schema — Water Log Entry
# =========================================================

class WaterLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    logged_at: date
    amount_ml: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# Response Schema — Combined Daily Water Summary
# =========================================================

class WaterDaySummaryOut(BaseModel):
    """
    Shape returned by GET /water-logs/day/{target_date}.

    Combines manual logging with food-derived water (from
    NutritionLog.water_ml) into one total — see
    WaterLogService.get_day_summary()'s docstring for the
    exact math, including the pacing fields.

    expected_so_far_ml / pace_status are None when the user
    hasn't set BOTH daily_water_ml_target and typical_wake_time
    yet — the pacing nudge simply has nothing to compare
    against until both exist.
    """

    logged_at: date
    manual_ml: float
    food_derived_ml: float
    total_ml: float
    target_ml: Optional[float] = None
    expected_so_far_ml: Optional[float] = None
    pace_status: Optional[str] = None  # "ahead" | "on_track" | "behind"