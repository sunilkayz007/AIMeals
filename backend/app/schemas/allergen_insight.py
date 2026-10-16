"""
=========================================================
AIMeals Backend
Allergen Insight Schema

Responsibilities:
    - Define response shapes for:
        GET  /ai/allergen-insight/{allergy_id}
        POST /ai/allergen-insight/{allergy_id}/deep

Example usage:
    from app.schemas.allergen_insight import AllergenInsightOut, AllergenDeepInsightOut
=========================================================
"""

from typing import Optional

from pydantic import BaseModel


class AllergenInsightOut(BaseModel):
    allergy_id: str
    allergy_name: str
    short_insight_text: str

    # True if the CURRENT user has already unlocked the deep
    # insight for this allergen — if True, deep_insight_text
    # is included for free (no extra credit charge, no extra
    # tap needed to fetch it again).
    is_unlocked: bool
    deep_insight_text: Optional[str] = None


class AllergenDeepInsightOut(BaseModel):
    deep_insight_text: str