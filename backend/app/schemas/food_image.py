"""
=========================================================
AIMeals Backend
Food Image Schemas

Responsibilities:
    - Define response shape for FoodImage (per-item detection)
    - Define the request shape for resolving one or more
      flagged item ambiguities

Notes:
    - fiber_g (per-item) and total_fiber_g (aggregate) added
      alongside the Home screen's 6-card redesign (Aug 2026),
      following the same shape as the other per-item nutrition
      fields — see app/models/food_image.py's detected_foods
      JSONB shape.

Example usage:
    from app.schemas.food_image import FoodImageOut

    def get_analysis(image: FoodImage) -> FoodImageOut:
        ...
=========================================================
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.food_image import FoodImageStatus


# =========================================================
# Response Schema — One Alternative for an Ambiguous Item
# =========================================================

class FoodItemAlternativeOut(BaseModel):
    """
    One entry in a food item's `alternatives` list — only
    present when that item's confidence was below ~0.85.
    Carries a FULL independent nutrition estimate, computed by
    Claude up front (not re-estimated on resolve), since the
    image is never saved for a later API call.
    """

    name: str
    confidence: Optional[float] = None
    reason: Optional[str] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    micronutrients: Optional[Dict[str, float]] = None


# =========================================================
# Response Schema — One Detected Food Item
# =========================================================

class FoodItemOut(BaseModel):
    """
    One independently-detected food item. alternatives is
    empty when Claude was confident; non-empty means this
    specific item (and only this item) is awaiting
    clarification — resolve via
    POST /ai/food-image/{image_id}/resolve.
    """

    name: str
    region: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    estimated_weight_g: Optional[float] = None
    visible_percentage: Optional[float] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    micronutrients: Optional[Dict[str, float]] = None
    alternatives: List[FoodItemAlternativeOut] = []


# =========================================================
# Response Schema — Food Image Analysis
# =========================================================

class FoodImageOut(BaseModel):
    """
    Shape of food image analysis data returned to the client.

    image_url will always be null — the raw image is never
    saved (see food_image.py's model docstring for why).

    status is PENDING while ANY item in `detected_foods` still
    has a non-empty `alternatives` list.

    total_calories/protein_g/carbs_g/fat_g/fiber_g are a plain
    sum across `detected_foods`, always internally consistent
    with the per-item breakdown (computed server-side, never
    asked from Claude as a separate number).
    """

    id: uuid.UUID
    user_id: uuid.UUID
    ai_interaction_id: Optional[uuid.UUID] = None
    image_url: Optional[str] = None
    status: FoodImageStatus
    meal_type: Optional[str] = None
    detected_foods: List[FoodItemOut]
    total_calories: Optional[float] = None
    total_protein_g: Optional[float] = None
    total_carbs_g: Optional[float] = None
    total_fat_g: Optional[float] = None
    total_fiber_g: Optional[float] = None
    total_micronutrients: Optional[Dict[str, float]] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# Request Schema — Resolve One Item's Ambiguity
# =========================================================

class ItemResolution(BaseModel):
    """
    One resolution choice: which food item (by its index in
    the analysis's `detected_foods` list), and which name the
    user confirmed — either that item's own original name (to
    confirm it was correct) or one of its alternatives[].name
    values (to switch to that alternative).
    """

    item_index: int
    chosen_label: str


# =========================================================
# Request Schema — Resolve Ambiguity (supports multiple items)
# =========================================================

class ResolveAmbiguityRequest(BaseModel):
    """
    Shape of the payload accepted by
    POST /ai/food-image/{image_id}/resolve.

    resolutions supports resolving MULTIPLE independently-
    ambiguous items in a single call — e.g. a frontend that
    shows every open question at once and submits all answers
    together. Each chosen_label must match one of that specific
    item's alternatives[].name values, case-insensitively.
    """

    resolutions: List[ItemResolution]
