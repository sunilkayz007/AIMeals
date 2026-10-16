"""
=========================================================
AIMeals Backend
Pantry Item Model

Responsibilities:
    - Define the pantry_items table schema

Dependencies:
    - app.B_database.Base
    - app.models.user.User

Notes:
    - Multiple rows per ingredient ARE allowed for the same
      user (e.g. two separate batches of eggs bought on
      different dates, each with its own expiration_date).
      This is deliberate: it's what makes accurate
      expiration-based prioritization possible for the
      Pantry Chef AI feature. "Total quantity of an
      ingredient" is computed by summing across rows at
      query time, which is a trivial cost compared to the
      alternative (losing per-batch expiration accuracy).
    - ingredient_name is freeform text for now, consistent
      with the same decision made on Recipe.ingredients —
      a full ingredient taxonomy is a bigger undertaking
      better suited for when Pantry Chef is actually built.

Example usage:
    from app.models.pantry_item import PantryItem

    item = PantryItem(
        user_id=user.id,
        ingredient_name="Eggs",
        quantity=12,
        unit="pieces",
        expiration_date=date(2026, 8, 10),
    )
=========================================================
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Pantry Item Model
# =========================================================

class PantryItem(Base):
    """
    Represents a single batch of an ingredient a user has on hand.

    Table: pantry_items
    """

    __tablename__ = "pantry_items"

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
    # Item Details
    # ---------------------------------------------------

    ingredient_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    added_at: Mapped[datetime] = mapped_column(
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
        return f"<PantryItem id={self.id} ingredient={self.ingredient_name} expires={self.expiration_date}>"