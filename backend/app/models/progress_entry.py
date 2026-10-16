"""
=========================================================
AIMeals Backend
Progress Entry Model

Responsibilities:
    - Define the progress_entries table schema

Dependencies:
    - app.B_database.Base
    - app.models.user.User

Notes:
    - This is the historical time-series counterpart to
      Profile.weight_kg, which only holds the CURRENT value.
      Progress is what enables trend charts over time.
    - Enforces one entry per user per day via a unique
      constraint on (user_id, recorded_date) — logging
      again on the same date should update the existing
      row, not create a duplicate.

Example usage:
    from app.models.progress_entry import ProgressEntry

    entry = ProgressEntry(
        user_id=user.id,
        recorded_date=date.today(),
        weight_kg=74.8,
    )
=========================================================
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Progress Entry Model
# =========================================================

class ProgressEntry(Base):
    """
    Represents a single day's weight/measurement log entry.

    Table: progress_entries
    """

    __tablename__ = "progress_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "recorded_date", name="uq_user_progress_date"),
    )

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Foreign Key
    # ---------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------
    # Entry Details
    # ---------------------------------------------------

    recorded_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    body_fat_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    chest_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hip_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user = relationship("User")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<ProgressEntry id={self.id} user_id={self.user_id} date={self.recorded_date} weight={self.weight_kg}>"