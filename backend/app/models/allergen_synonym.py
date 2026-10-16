"""
=========================================================
AIMeals Backend
Allergen Synonym Model

Responsibilities:
    - Define the allergen_synonyms table schema

Dependencies:
    - app.B_database.Base
    - app.models.allergy.Allergy

Notes:
    - This moves allergen synonym coverage from a hardcoded
      Python dict into the database, so it can be expanded
      or corrected without a code deploy (e.g. by an admin
      tool later). This does NOT make the coverage medically
      exhaustive by itself — see the seed script for the
      actual baseline data, grounded in the FDA's 9
      recognized major food allergens as a starting point,
      not a complete list of every possible allergen or
      cross-contamination source.

Example usage:
    from app.models.allergen_synonym import AllergenSynonym

    synonym = AllergenSynonym(allergy_id=peanuts.id, synonym="groundnut")
=========================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Allergen Synonym Model
# =========================================================

class AllergenSynonym(Base):
    """
    Represents a single synonym/variant term for an allergy
    (e.g. "groundnut" for "Peanuts").

    Table: allergen_synonyms
    """

    __tablename__ = "allergen_synonyms"
    __table_args__ = (
        UniqueConstraint("allergy_id", "synonym", name="uq_allergy_synonym"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    allergy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("allergies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    synonym: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    allergy = relationship("Allergy")

    def __repr__(self) -> str:
        return f"<AllergenSynonym allergy_id={self.allergy_id} synonym={self.synonym}>"