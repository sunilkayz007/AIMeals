"""
=========================================================
AIMeals Backend
Water Log Model

Responsibilities:
    - Define the water_logs table schema — manual water
      entries (glass/bottle taps), separate from the
      food-derived water tracked on NutritionLog.water_ml.

Notes:
    - A user's total daily water intake = SUM(water_logs for
      the day) + SUM(nutrition_logs.water_ml for the day) —
      combined at read time in WaterLogService, not stored as
      one merged number, so each source stays independently
      auditable/editable.
    - No portion_percentage/scaling here — a manual water log
      is already the exact amount the user says they drank.

Example usage:
    from app.models.water_log import WaterLog

    log = WaterLog(user_id=user.id, logged_at=date.today(), amount_ml=250)
=========================================================
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Water Log Model
# =========================================================

class WaterLog(Base):
    """
    Represents a single manual water-intake entry.

    Table: water_logs
    """

    __tablename__ = "water_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Same logged_at/created_at split as NutritionLog — logged_at
    # is the day this counts toward (user-controlled), created_at
    # is when the row was actually inserted (system-controlled).
    logged_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    amount_ml: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<WaterLog id={self.id} user_id={self.user_id} amount_ml={self.amount_ml}>"