"""
=========================================================
AIMeals Backend
Meal Plan Chunk Model

Responsibilities:
    - Define the meal_plan_chunks table schema
    - Define the MealPlanChunkStatus enum

Notes:
    - A large meal plan (e.g. a full week with all 4 meal
      types) can't be generated in a single Claude call
      without risking truncation — see
      AIService.generate_meal_plan()'s docstring for the full
      reasoning. Instead, a plan's date range is split into
      chunks of CHUNK_SIZE_DAYS calendar days each; chunk 1
      generates synchronously at plan-creation time, and every
      later chunk generates lazily, the next time the plan's
      meals are fetched via the AI-aware route AFTER that
      chunk's scheduled_generate_at date has passed.
    - This is pull-based, not a background worker — there is
      no separate scheduler process. "Due" chunks are checked
      and generated inline, synchronously, as part of
      answering a GET request. See
      AIService.sync_due_meal_plan_chunks().
    - status stays PENDING if a due chunk couldn't generate
      because the user was out of credits at that moment —
      it'll be retried the next time the plan is opened,
      rather than marked FAILED (which is reserved for a
      genuine generation/parsing failure, mirroring how
      FoodImageStatus/ReportStatus use status to mean
      "outcome," not "attempted").

Example usage:
    from app.models.meal_plan_chunk import MealPlanChunk, MealPlanChunkStatus
=========================================================
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Status Enum
# =========================================================

class MealPlanChunkStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# =========================================================
# Meal Plan Chunk Model
# =========================================================

class MealPlanChunk(Base):
    """
    One generation batch within a larger meal plan.

    Table: meal_plan_chunks
    """

    __tablename__ = "meal_plan_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    meal_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meal_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 0-indexed order within the plan — chunk 0 is the one
    # generated synchronously at plan creation.
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # The date on/after which this chunk becomes eligible to
    # generate. Chunk 0's is the plan-creation date (generates
    # immediately regardless); every later chunk's is set with
    # a one-day buffer before its own start_date, so it's
    # ready before those days are actually needed.
    scheduled_generate_at: Mapped[date] = mapped_column(Date, nullable=False)

    # Stored here (not on MealPlan) so each chunk is fully
    # self-contained and can regenerate independently, however
    # much later it actually runs — comma-separated MealType
    # values, e.g. "breakfast,lunch,dinner".
    meal_types: Mapped[str] = mapped_column(String(200), nullable=False)
    preferences: Mapped[str] = mapped_column(Text, nullable=False, default="")

    status: Mapped[MealPlanChunkStatus] = mapped_column(
        Enum(MealPlanChunkStatus, name="meal_plan_chunk_status"),
        nullable=False,
        default=MealPlanChunkStatus.PENDING,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    meal_plan = relationship("MealPlan")

    def __repr__(self) -> str:
        return (
            f"<MealPlanChunk id={self.id} plan={self.meal_plan_id} "
            f"idx={self.chunk_index} status={self.status}>"
        )