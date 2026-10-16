"""
=========================================================
AIMeals Backend
Allergy General Facts Repository

Responsibilities:
    - Read/create/update allergy_general_facts rows
    - Contains NO business logic (refresh-timing decisions
      live in AIService.get_allergy_general_facts())

Example usage:
    from app.repositories.allergy_general_facts_repository import (
        AllergyGeneralFactsRepository,
    )

    repo = AllergyGeneralFactsRepository(db)
    existing = repo.get_for_user(user.id)
=========================================================
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.allergy_general_facts import AllergyGeneralFacts


# =========================================================
# Allergy General Facts Repository
# =========================================================

class AllergyGeneralFactsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, user_id: uuid.UUID) -> Optional[AllergyGeneralFacts]:
        return (
            self.db.query(AllergyGeneralFacts)
            .filter(AllergyGeneralFacts.user_id == user_id)
            .first()
        )

    def create(
        self, user_id: uuid.UUID, facts: list[dict], allergy_signature: str
    ) -> AllergyGeneralFacts:
        row = AllergyGeneralFacts(
            user_id=user_id, facts=facts, allergy_signature=allergy_signature
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update(
        self, row: AllergyGeneralFacts, facts: list[dict], allergy_signature: str
    ) -> AllergyGeneralFacts:
        row.facts = facts
        row.allergy_signature = allergy_signature
        self.db.commit()
        self.db.refresh(row)
        return row