"""
=========================================================
AIMeals Backend
Food Image Model

Responsibilities:
    - Define the food_images table schema
    - Define the FoodImageStatus enum

Dependencies:
    - app.B_database.Base
    - app.models.user.User
    - app.models.ai_interaction.AIInteraction (FK)

Notes:
    - detected_foods is a JSONB list of per-item dicts, each
      shaped like:
        {
          "name": str, "region": str | None,
          "confidence": float, "reason": str,
          "estimated_weight_g": float | None,
          "visible_percentage": float,
          "calories": float, "protein_g": float,
          "carbs_g": float, "fat_g": float, "water_ml": float,
          "fiber_g": float,
          "alternatives": [ ...same nutrition fields... ]
        }
      See AIService._FOOD_IMAGE_ANALYSIS_SYSTEM_PROMPT for the
      exact schema Claude is asked to return.
    - total_calories/total_protein_g/total_carbs_g/total_fat_g/
      total_water_ml/total_fiber_g are plain sums across
      detected_foods, computed in Python
      (AIService.analyze_food_image()), not asked from Claude
      as a separate aggregate — keeps the total from ever
      drifting out of sync with the per-item breakdown.
    - total_water_ml added 2026-08-07, mirroring
      recipes.water_ml_per_serving / nutrition_logs.water_ml —
      same "Claude estimate from ingredient moisture, not a
      precise measurement" caveat applies. total_fiber_g added
      alongside the Home screen's 6-card redesign (Aug 2026),
      same caveat.
    - status starts PENDING if any detected item has
      alternatives (genuine ambiguity Claude wasn't confident
      enough to resolve on its own) and CONFIRMED otherwise.
      A PENDING scan must be resolved (see
      AIService.resolve_food_image_ambiguity()) before it can
      be logged as a meal — see
      NutritionLogService.log_meal_from_food_image().
    - No image is ever stored server-side (cost decision) —
      image_url is populated only if/while the client holds a
      transient reference for display; nothing durable is kept.

Example usage:
    from app.models.food_image import FoodImage, FoodImageStatus

    scan = FoodImage(
        user_id=user.id,
        status=FoodImageStatus.CONFIRMED,
        detected_foods=[{"name": "Dal", "calories": 180, ...}],
        total_calories=180,
    )
=========================================================
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Food Image Status Enum
# =========================================================

class FoodImageStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"


# =========================================================
# Food Image Model
# =========================================================

class FoodImage(Base):
    """
    Represents one food-photo analysis — the foods Claude
    detected in it, their estimated nutrition, and the
    confirmed/pending resolution state.

    Table: food_images
    """

    __tablename__ = "food_images"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Foreign Keys
    # ---------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ai_interaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_interactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---------------------------------------------------
    # Analysis Details
    # ---------------------------------------------------

    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    status: Mapped[FoodImageStatus] = mapped_column(
        Enum(FoodImageStatus, name="food_image_status"),
        nullable=False,
        default=FoodImageStatus.CONFIRMED,
    )

    meal_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # [{"name": ..., "calories": ..., "water_ml": ..., "fiber_g": ..., "alternatives": [...]}, ...]
    detected_foods: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # ---------------------------------------------------
    # Totals (summed in Python from detected_foods, see
    # module notes — never asked from Claude directly)
    # ---------------------------------------------------

    total_calories: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_protein_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_carbs_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_fat_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Added 2026-08-07 — see module notes.
    total_water_ml: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Added alongside the Home screen's 6-card redesign (Aug
    # 2026) — see module notes.
    total_fiber_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Added alongside the 10-nutrient vitamin/mineral tracking
    # feature (Aug 2026) — see nutrition_log.py's micronutrients
    # column comment for why this is one JSONB dict rather than 10
    # separate float columns. This is the summed TOTAL across
    # detected_foods (same "computed in Python, never asked from
    # Claude as a separate aggregate" rule as total_calories etc.).
    total_micronutrients: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user = relationship("User")
    ai_interaction = relationship("AIInteraction")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<FoodImage id={self.id} user_id={self.user_id} status={self.status}>"
