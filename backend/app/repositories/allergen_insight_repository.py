"""
=========================================================
AIMeals Backend
Allergen Insight Repository

Responsibilities:
    - Read/create/update allergen_insights rows (shared
      per-allergen cache)
    - Read/create user_allergen_deep_unlocks rows (per-user
      unlock tracking, backs the "don't re-charge for content
      already unlocked" rule — see
      AIService.get_allergen_deep_insight()'s docstring)
    - Contains NO business logic

Example usage:
    from app.repositories.allergen_insight_repository import (
        AllergenInsightRepository,
        UserAllergenDeepUnlockRepository,
    )

    insight_repo = AllergenInsightRepository(db)
    unlock_repo = UserAllergenDeepUnlockRepository(db)
=========================================================
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.allergen_insight import AllergenInsight, UserAllergenDeepUnlock


# =========================================================
# Allergen Insight Repository (shared per-allergen cache)
# =========================================================

class AllergenInsightRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_allergy(self, allergy_id: uuid.UUID) -> Optional[AllergenInsight]:
        return (
            self.db.query(AllergenInsight)
            .filter(AllergenInsight.allergy_id == allergy_id)
            .first()
        )

    def create_short(self, allergy_id: uuid.UUID, short_insight_text: str) -> AllergenInsight:
        row = AllergenInsight(allergy_id=allergy_id, short_insight_text=short_insight_text)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def set_deep(self, row: AllergenInsight, deep_insight_text: str) -> AllergenInsight:
        from sqlalchemy import func

        row.deep_insight_text = deep_insight_text
        row.deep_generated_at = func.now()
        self.db.commit()
        self.db.refresh(row)
        return row


# =========================================================
# User Allergen Deep Unlock Repository
# =========================================================

class UserAllergenDeepUnlockRepository:
    def __init__(self, db: Session):
        self.db = db

    def has_unlocked(self, user_id: uuid.UUID, allergy_id: uuid.UUID) -> bool:
        return (
            self.db.query(UserAllergenDeepUnlock)
            .filter(
                UserAllergenDeepUnlock.user_id == user_id,
                UserAllergenDeepUnlock.allergy_id == allergy_id,
            )
            .first()
            is not None
        )

    def create(self, user_id: uuid.UUID, allergy_id: uuid.UUID) -> UserAllergenDeepUnlock:
        row = UserAllergenDeepUnlock(user_id=user_id, allergy_id=allergy_id)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row