"""
=========================================================
AIMeals Backend
Meal Plan Chunk Repository

Responsibilities:
    - Perform CRUD operations against meal_plan_chunks
    - Contains NO business logic

Dependencies:
    - app.models.meal_plan_chunk.MealPlanChunk
=========================================================
"""

import uuid
from datetime import date
from typing import List

from sqlalchemy.orm import Session

from app.models.meal_plan_chunk import MealPlanChunk, MealPlanChunkStatus


class MealPlanChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_plan(self, meal_plan_id: uuid.UUID) -> List[MealPlanChunk]:
        return (
            self.db.query(MealPlanChunk)
            .filter(MealPlanChunk.meal_plan_id == meal_plan_id)
            .order_by(MealPlanChunk.chunk_index)
            .all()
        )

    def get_due_pending(self, meal_plan_id: uuid.UUID, as_of: date) -> List[MealPlanChunk]:
        """
        Chunks still PENDING whose scheduled_generate_at has
        already passed — the set that
        AIService.sync_due_meal_plan_chunks() should generate,
        in order.
        """
        return (
            self.db.query(MealPlanChunk)
            .filter(
                MealPlanChunk.meal_plan_id == meal_plan_id,
                MealPlanChunk.status == MealPlanChunkStatus.PENDING,
                MealPlanChunk.scheduled_generate_at <= as_of,
            )
            .order_by(MealPlanChunk.chunk_index)
            .all()
        )

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        meal_plan_id: uuid.UUID,
        chunk_index: int,
        start_date: date,
        end_date: date,
        scheduled_generate_at: date,
        meal_types: str,
        preferences: str,
    ) -> MealPlanChunk:
        new_chunk = MealPlanChunk(
            meal_plan_id=meal_plan_id,
            chunk_index=chunk_index,
            start_date=start_date,
            end_date=end_date,
            scheduled_generate_at=scheduled_generate_at,
            meal_types=meal_types,
            preferences=preferences,
        )
        self.db.add(new_chunk)
        self.db.commit()
        self.db.refresh(new_chunk)
        return new_chunk

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update_status(self, chunk: MealPlanChunk, status: MealPlanChunkStatus) -> MealPlanChunk:
        chunk.status = status
        self.db.commit()
        self.db.refresh(chunk)
        return chunk