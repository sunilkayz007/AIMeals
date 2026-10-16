"""
=========================================================
AIMeals Backend
Allergen Checker

Responsibilities:
    - Deterministically scan generated recipe text for a
      user's known allergens, including database-backed
      synonyms
    - Provide a safety backstop that does NOT rely on the
      AI model correctly following prompt instructions

Dependencies:
    - app.repositories.allergy_repository.UserAllergyRepository
    - app.repositories.allergen_synonym_repository.AllergenSynonymRepository

Notes:
    - THIS IS DEFENSE-IN-DEPTH, NOT A GUARANTEE. Text
      matching cannot catch every synonym, cross-
      contamination warning, or ambiguous ingredient
      ("natural flavors" could hide almost anything). It
      catches known failures where an allergen name or a
      recorded synonym literally appears in the generated
      text. Given the real-world consequences of an allergic
      reaction, this should be treated as one layer of
      protection alongside prompt instructions and clear
      user-facing disclaimers, not as a complete solution.
    - Synonyms now live in the database (allergen_synonyms
      table) rather than a hardcoded dict, so coverage can
      be expanded or corrected without a code deploy. See
      the seed script (scripts/seed_allergen_synonyms.py)
      for the baseline data — grounded in the FDA's 9
      recognized major food allergens, not exhaustive.
    - An allergy with no synonyms recorded in the database
      (e.g. a rare, user-typed allergy name) still gets
      checked against its own exact name — synonyms are an
      addition, not a replacement for exact-name matching.

Example usage:
    from app.ai.allergen_checker import AllergenChecker

    checker = AllergenChecker(db)
    violations = checker.check_recipe_text(user_id, ingredients_text, instructions_text)
    if violations:
        # reject the recipe — do not save or return it
        ...
=========================================================
"""

import uuid
from typing import List

from sqlalchemy.orm import Session

from app.repositories.allergen_synonym_repository import AllergenSynonymRepository
from app.repositories.allergy_repository import UserAllergyRepository


# =========================================================
# Allergen Checker
# =========================================================

class AllergenChecker:
    """
    Deterministically checks generated recipe text against
    a user's known allergies and their database-recorded
    synonyms. Makes no API calls.
    """

    def __init__(self, db: Session):
        self.db = db
        self.user_allergy_repo = UserAllergyRepository(db)
        self.synonym_repo = AllergenSynonymRepository(db)

    def check_recipe_text(
        self,
        user_id: uuid.UUID,
        *texts: str,
    ) -> List[str]:
        """
        Checks the given text(s) (typically ingredients and
        instructions) against the user's known allergies and
        their recorded synonyms.

        Returns a list of allergy names that were detected as
        present in the text. An empty list means no known
        allergen terms were found — NOT a guarantee the
        recipe is safe, only that this check found nothing.

        Usage:
            violations = checker.check_recipe_text(
                user_id, recipe.ingredients, recipe.instructions
            )
        """
        user_allergies = self.user_allergy_repo.get_for_user(user_id)

        if not user_allergies:
            return []

        combined_text = " ".join(texts).lower()

        violations: List[str] = []

        for link in user_allergies:
            allergy_name = link.allergy.name
            terms_to_check = [allergy_name.lower()]

            synonym_rows = self.synonym_repo.get_by_allergy_id(link.allergy_id)
            terms_to_check.extend(row.synonym for row in synonym_rows)

            if any(term in combined_text for term in terms_to_check):
                violations.append(allergy_name)

        return violations