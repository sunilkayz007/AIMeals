"""
=========================================================
AIMeals Backend
Ingredient Scan Model

Responsibilities:
    - Define the ingredient_scans table schema
    - Define the IngredientScanStatus enum

Dependencies:
    - app.B_database.Base (declarative base)

Example usage:
    from app.models.ingredient_scan import IngredientScan, IngredientScanStatus

    new_scan = IngredientScan(
        user_id=user.id,
        ingredients=[{"name": "Zucchini", "confidence_note": None}],
    )
=========================================================
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.B_database import Base


# =========================================================
# Status Enum
# =========================================================

class IngredientScanStatus(str, enum.Enum):
    """
    Defines the lifecycle of an ingredient scan.

    Stored in the database as a native Postgres ENUM type,
    so invalid values are rejected at the database level,
    not just in application code.
    """
    PENDING = "pending"
    CONFIRMED = "confirmed"


# =========================================================
# IngredientScan Model
# =========================================================

class IngredientScan(Base):
    """
    Represents a single ingredient-photo identification pass,
    awaiting user confirmation/correction before it's used to
    generate a recipe.

    Table: ingredient_scans
    """

    __tablename__ = "ingredient_scans"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Ownership
    # ---------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ---------------------------------------------------
    # Scan Data
    # ---------------------------------------------------

    ingredients: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    status: Mapped[IngredientScanStatus] = mapped_column(
        Enum(IngredientScanStatus, name="ingredient_scan_status"),
        default=IngredientScanStatus.PENDING,
        nullable=False,
    )

    # ---------------------------------------------------
    # AI Audit Link
    # ---------------------------------------------------

    ai_interaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_interactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Representation
    # ----------------------------------------