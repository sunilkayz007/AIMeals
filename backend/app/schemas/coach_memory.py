"""
=========================================================
AIMeals Backend
Coach Memory Schema

Responsibilities:
    - Define response shapes for GET/DELETE /api/v1/coach/memory

Example usage:
    from app.schemas.coach_memory import CoachMemoryFactOut, CoachMemoryListOut
=========================================================
"""

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel


class CoachMemoryFactOut(BaseModel):
    id: UUID
    fact: str
    created_at: datetime

    class Config:
        from_attributes = True


class CoachMemoryListOut(BaseModel):
    facts: List[CoachMemoryFactOut]


class CoachMemoryClearOut(BaseModel):
    cleared_count: int
