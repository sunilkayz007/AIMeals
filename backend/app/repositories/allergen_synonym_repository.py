"""
=========================================================
AIMeals Backend
Allergen Synonym Repository

Responsibilities:
    - Perform CRUD operations against the allergen_synonyms table
    - Contains NO business logic

Dependencies:
    - app.models.allergen_synonym.AllergenSynonym

Example usage:
    from app.repositories.allergen_synonym_repository import AllergenSynonymRepository

    repo = AllergenSynonymRepository(db)
    synonyms = repo.get_by_allergy_id(peanuts.id)
=========================================================
"""

import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.allergen_synonym import AllergenSynonym


# =========================================================
# Allergen Synonym Repository
# =========================================================

class AllergenSynonymRepository:
    """
    Encapsulates all direct database access for the AllergenSynonym model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_allergy_id(self, allergy_id: uuid.UUID) -> List[AllergenSynonym]:
        return (
            self.db.query(AllergenSynonym)
            .filter(AllergenSynonym.allergy_id == allergy_id)
            .all()
        )

    def exists(self, allergy_id: uuid.UUID, synonym: str) -> bool:
        return (
            self.db.query(AllergenSynonym)
            .filter(
                AllergenSynonym.allergy_id == allergy_id,
                AllergenSynonym.synonym == synonym.lower(),
            )
            .first()
            is not None
        )

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(self, allergy_id: uuid.UUID, synonym: str) -> AllergenSynonym:
        new_synonym = AllergenSynonym(allergy_id=allergy_id, synonym=synonym.lower())
        self.db.add(new_synonym)
        self.db.commit()
        self.db.refresh(new_synonym)
        return new_synonym

    def bulk_create(self, allergy_id: uuid.UUID, synonyms: List[str]) -> List[AllergenSynonym]:
        """
        Creates multiple synonyms for one allergy, skipping
        any that already exist (safe to call repeatedly, e.g.
        from a seed script, without creating duplicates).
        """
        created = []
        for synonym in synonyms:
            if not self.exists(allergy_id, synonym):
                created.append(self.create(allergy_id, synonym))
        return created

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete(self, synonym_row: AllergenSynonym) -> None:
        self.db.delete(synonym_row)
        self.db.commit()