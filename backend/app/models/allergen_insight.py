"""
=========================================================
AIMeals Backend
Allergen Insight Model

Responsibilities:
    - Define the allergen_insights table schema — a cache
      keyed by the MASTER allergen (not per-user), backing
      the "About your allergies" tap-through detail screen.

Notes:
    - Deliberately keyed by allergy_id, not (user_id, allergy_id)
      — the content ("how peanuts commonly hide in dishes")
      doesn't depend on who's asking, only on which allergen.
      This means a given allergen's insight is generated AT
      MOST ONCE ever, total, across the whole user base, and
      every subsequent request (from any user) for the same
      allergen is a cache hit with no Claude call.
    - short_insight_text (Haiku) is free and generated
      automatically on first request. deep_insight_text
      (Sonnet) is generated on first PAID request for that
      allergen and reused after that — see
      AIService.get_allergen_deep_insight()'s docstring for
      the credit-charging logic (which is per-USER unlock,
      tracked separately in UserAllergenDeepUnlock, NOT
      re-charged just because this cached text already exists
      from some other user's earlier unlock).

Example usage:
    from app.models.allergen_insight import AllergenInsight

    row = AllergenInsight(
        allergy_id=allergy.id,
        short_insight_text="Peanuts often hide in...",
    )
=========================================================
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Allergen Insight Model
# =========================================================

class AllergenInsight(Base):
    """
    Represents the cached short (free/Haiku) and deep
    (paid/Sonnet) insight text for one master allergen.
    Exactly one row per allergen, shared across every user.

    Table: allergen_insights
    """

    __tablename__ = "allergen_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    allergy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("allergies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    short_insight_text: Mapped[str] = mapped_column(Text, nullable=False)
    short_generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Null until the first paid user unlocks it for this allergen.
    deep_insight_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deep_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    allergy = relationship("Allergy")

    def __repr__(self) -> str:
        return f"<AllergenInsight id={self.id} allergy_id={self.allergy_id}>"


# =========================================================
# Per-User Deep Insight Unlock
# =========================================================

class UserAllergenDeepUnlock(Base):
    """
    Tracks which (user, allergen) pairs a user has already
    paid a credit to unlock the deep insight for. Prevents
    re-charging a user every time they reopen an allergen
    detail they've already unlocked — the credit buys
    permanent access to that allergen's deep insight, not a
    single view.

    Table: user_allergen_deep_unlocks
    """

    __tablename__ = "user_allergen_deep_unlocks"

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

    allergy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("allergies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User")
    allergy = relationship("Allergy")

    def __repr__(self) -> str:
        return f"<UserAllergenDeepUnlock user_id={self.user_id} allergy_id={self.allergy_id}>"