"""
=========================================================
AIMeals Backend
Daily Tip Model

Responsibilities:
    - Define the daily_tips table schema — a one-row-per-
      user-per-day cache backing the "Tips for you" Home
      screen feature.

Dependencies:
    - app.B_database.Base
    - app.models.user.User

Notes:
    - The (user_id, tip_date) unique constraint (defined in
      the migration, not here as a model-level constraint,
      matching this codebase's existing convention) is what
      actually enforces the caching guarantee — see
      AIService.get_daily_tip()'s docstring for the full flow.
    - No update() capability needed — a tip is generated once
      per day and never edited afterward.

Example usage:
    from app.models.daily_tip import DailyTip

    tip = DailyTip(
        user_id=user.id,
        tip_date=date.today(),
        tip_text="You've got room for a protein-rich snack today!",
    )
=========================================================
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Daily Tip Model
# =========================================================

class DailyTip(Base):
    """
    Represents a single cached daily tip for one user.

    Table: daily_tips
    """

    __tablename__ = "daily_tips"

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

    tip_date: Mapped[date] = mapped_column(Date, nullable=False)
    tip_text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<DailyTip id={self.id} user_id={self.user_id} tip_date={self.tip_date}>"