"""
=========================================================
AIMeals Backend
Allergy & Dietary Restriction Models

Responsibilities:
    - Define master lookup tables for allergies and
      dietary restrictions (admin-managed reference data)
    - Define junction tables linking users to their
      specific allergies/restrictions

Dependencies:
    - app.B_database.Base
    - app.models.user.User

Notes:
    - Allergy and DietaryRestriction are LOOKUP tables —
      a small, shared, admin-managed list (e.g. "Peanuts",
      "Vegetarian"). They are not user-specific.
    - UserAllergy and UserDietaryRestriction are JUNCTION
      tables linking a specific user to specific entries
      in those lookup tables.
    - Junction tables link to user_id directly (not
      profile_id), so allergy/restriction data can be
      recorded immediately at signup, independent of
      whether the user has completed their full profile.
      This matters for a severe allergy, which is safety-
      relevant data that shouldn't be gated behind an
      optional form.

Example usage:
    from app.models.allergy import Allergy, UserAllergy, AllergySeverity

    peanut_allergy = Allergy(name="Peanuts")

    user_link = UserAllergy(
        user_id=user.id,
        allergy_id=peanut_allergy.id,
        severity=AllergySeverity.SEVERE,
    )
=========================================================
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Severity Enum
# =========================================================

class AllergySeverity(str, enum.Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


# =========================================================
# Allergy Lookup Table
# =========================================================

class Allergy(Base):
    """
    Master list of known allergies (e.g. Peanuts, Shellfish, Gluten).

    Table: allergies
    This is reference data, not user-specific.
    """

    __tablename__ = "allergies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Allergy id={self.id} name={self.name}>"


# =========================================================
# Dietary Restriction Lookup Table
# =========================================================

class DietaryRestriction(Base):
    """
    Master list of known dietary restrictions
    (e.g. Vegetarian, Vegan, Halal, Keto).

    Table: dietary_restrictions
    This is reference data, not user-specific.
    """

    __tablename__ = "dietary_restrictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<DietaryRestriction id={self.id} name={self.name}>"


# =========================================================
# User <-> Allergy Junction Table
# =========================================================

class UserAllergy(Base):
    """
    Links a user to a specific allergy, with severity.

    Table: user_allergies
    """

    __tablename__ = "user_allergies"
    __table_args__ = (
        UniqueConstraint("user_id", "allergy_id", name="uq_user_allergy"),
    )

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

    severity: Mapped[AllergySeverity] = mapped_column(
        Enum(AllergySeverity, name="allergy_severity"),
        default=AllergySeverity.MODERATE,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User")
    allergy = relationship("Allergy")

    def __repr__(self) -> str:
        return f"<UserAllergy user_id={self.user_id} allergy_id={self.allergy_id} severity={self.severity}>"


# =========================================================
# User <-> Dietary Restriction Junction Table
# =========================================================

class UserDietaryRestriction(Base):
    """
    Links a user to a specific dietary restriction.

    Table: user_dietary_restrictions
    """

    __tablename__ = "user_dietary_restrictions"
    __table_args__ = (
        UniqueConstraint("user_id", "restriction_id", name="uq_user_restriction"),
    )

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

    restriction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dietary_restrictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User")
    restriction = relationship("DietaryRestriction")

    def __repr__(self) -> str:
        return f"<UserDietaryRestriction user_id={self.user_id} restriction_id={self.restriction_id}>"