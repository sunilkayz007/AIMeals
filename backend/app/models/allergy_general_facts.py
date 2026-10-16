"""
=========================================================
AIMeals Backend
Allergy General Facts Model

Responsibilities:
    - Define the allergy_general_facts table schema — a
      one-row-per-user cache backing the "Things you might
      not know" section of the Allergies screen.

Notes:
    - facts is a JSONB list of exactly 3 {text, category}
      objects, matching AIService.get_allergy_general_facts()'s
      contract with the Haiku system prompt.
    - allergy_signature is a stable string derived from the
      user's current allergy names (sorted, joined) — used to
      detect "the user's allergy list changed since these
      facts were generated" without needing a login-count
      column anywhere (see get_allergy_general_facts()'s
      docstring for the full refresh logic this backs).
    - Only one row per user ever exists — refreshes UPDATE
      this row rather than inserting a new one, unlike
      DailyTip which intentionally keeps one row per day.

Example usage:
    from app.models.allergy_general_facts import AllergyGeneralFacts

    row = AllergyGeneralFacts(
        user_id=user.id,
        facts=[{"text": "...", "category": "epidemiology"}, ...],
        allergy_signature="peanuts|shellfish",
    )
=========================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Allergy General Facts Model
# =========================================================

class AllergyGeneralFacts(Base):
    """
    Represents the cached "Things you might not know" facts
    for one user. Exactly one row per user.

    Table: allergy_general_facts
    """

    __tablename__ = "allergy_general_facts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # [{"text": str, "category": str}, ...] — always exactly 3 entries.
    facts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)

    allergy_signature: Mapped[str] = mapped_column(String(500), nullable=False)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<AllergyGeneralFacts id={self.id} user_id={self.user_id}>"