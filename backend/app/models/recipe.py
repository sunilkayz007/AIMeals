"""
=========================================================
AIMeals Backend
Recipe Model

Responsibilities:
    - Define the recipes table schema

Dependencies:
    - app.B_database.Base
    - app.models.user.User (nullable FK)

Notes:
    - created_by_user_id is NULLABLE: null means a system/
      curated recipe (seeded centrally, shared across all
      users); non-null means a specific user generated or
      saved it.
    - ingredients and instructions are kept as freeform
      TEXT for now, deliberately. A more "proper" design
      would be a relational RecipeIngredient table (each
      ingredient with its own quantity/unit), similar to
      how allergies were modeled. That is real added scope
      not needed yet — this model's immediate job is to
      unblock NutritionLog's optional FK. Revisit this
      when building the AI Recipe Generator (Phase 8),
      where structured ingredients start to matter for
      features like the Pantry Chef.
    - UPDATED (fail-open-with-confirmation allergen design):
      contains_allergen/flagged_allergens are DISPLAY fields
      only (e.g. driving the red-fill warning in the app).
      They answer "does this recipe contain an allergen."
      They are NOT the legal consent record — that's the
      separate, permanent AllergenOverrideConsent table
      (app/models/allergen_consent.py), which answers "did
      the user see a specific warning and agree to it." Do
      not conflate the two; a recipe could theoretically have
      contains_allergen=True with its consent record having
      been separately deleted/corrupted without that being
      visible here, which is exactly why the consent table
      exists independently rather than just being "the reason
      this flag is true."

Example usage:
    from app.models.recipe import Recipe

    recipe = Recipe(
        created_by_user_id=user.id,
        title="Grilled Chicken Salad",
        instructions="1. Grill chicken...\\n2. Chop vegetables...",
        ingredients="200g chicken breast\\n1 cup lettuce\\n...",
        servings=2,
        calories_per_serving=450,
    )
=========================================================
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Recipe Model
# =========================================================

class Recipe(Base):
    """
    Represents a recipe — either system-curated or
    generated/saved by a specific user.

    Table: recipes
    """

    __tablename__ = "recipes"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Foreign Key (nullable — null = system recipe)
    # ---------------------------------------------------

    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------
    # Content
    # ---------------------------------------------------

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    ingredients: Mapped[str] = mapped_column(Text, nullable=False)

    # ---------------------------------------------------
    # Timing / Yield
    # ---------------------------------------------------

    prep_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cook_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ---------------------------------------------------
    # Nutrition (per serving)
    # ---------------------------------------------------

    calories_per_serving: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    protein_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fat_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Added 2026-08-06 — estimated water content per serving,
    # from ingredient moisture (broth, vegetables, etc.). This is
    # a Claude estimate, not a database-backed figure the way
    # calories loosely trace back to food-composition data — the
    # frontend should present it as approximate.
    water_ml_per_serving: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Added alongside the Home screen's 6-card redesign (Aug
    # 2026) — same "Claude estimate, present as approximate"
    # caveat as water_ml_per_serving above.
    fiber_g_per_serving: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Added alongside the 10-nutrient vitamin/mineral tracking
    # feature (Aug 2026) — see nutrition_log.py's micronutrients
    # column comment for why this is one JSONB dict rather than 10
    # separate float columns. Per-serving, same as the other
    # nutrition fields on this model.
    micronutrients: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ---------------------------------------------------
    # Allergen Warning (DISPLAY fields — see module docstring
    # for why this is deliberately separate from the legal
    # consent record)
    # ---------------------------------------------------

    contains_allergen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flagged_allergens: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)

    # ---------------------------------------------------
    # Metadata
    # ---------------------------------------------------

    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

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

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    created_by = relationship("User")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<Recipe id={self.id} title={self.title}>"
