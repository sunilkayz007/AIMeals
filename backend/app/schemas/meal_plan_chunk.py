"""
=========================================================
AIMeals Backend
Meal Plan Chunk Schemas

Responsibilities:
    - Define the response shape for exposing a plan's chunk
      schedule/status to the frontend

Notes:
    - Read-only — chunks are never created/updated directly
      via the API, only as a side effect of meal plan
      generation (see AIService).

Example usage:
    from app.schemas.meal_plan_chunk import MealPlanChunkOut
=========================================================
"""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.meal_plan_chunk import MealPlanChunkStatus


class MealPlanChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    start_date: date
    end_date: date
    status: MealPlanChunkStatus