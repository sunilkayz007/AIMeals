"""
=========================================================
AIMeals Backend
Allergen Override Consent Repository

Responsibilities:
    - Insert and look up allergen_override_consents rows
    - Contains NO business logic

Dependencies:
    - app.models.allergen_consent.AllergenOverrideConsent

Notes:
    - DELIBERATELY has no update() or delete() method. This
      table is insert-only — see the model's docstring for
      why. If a genuine need for either ever arises, that
      should be a deliberate, separately-discussed addition,
      not something that quietly exists just because other
      repositories in this codebase have the shape.

Example usage:
    from app.repositories.allergen_consent_repository import AllergenConsentRepository

    repo = AllergenConsentRepository(db)
    consent = repo.create(
        user_id=user.id,
        recipe_id=recipe.id,
        user_email_snapshot=user.email,
        user_name_snapshot=f"{user.first_name} {user.last_name}",
        recipe_title_snapshot=recipe.title,
        flagged_allergens=["peanuts"],
        warning_text_shown="...",
    )
=========================================================
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.allergen_consent import AllergenOverrideConsent


# =========================================================
# Allergen Override Consent Repository
# =========================================================

class AllergenConsentRepository:
    """
    Encapsulates all direct database access for the
    AllergenOverrideConsent model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_id(self, consent_id: uuid.UUID) -> Optional[AllergenOverrideConsent]:
        return (
            self.db.query(AllergenOverrideConsent)
            .filter(AllergenOverrideConsent.id == consent_id)
            .first()
        )

    def get_by_user(self, user_id: uuid.UUID) -> List[AllergenOverrideConsent]:
        """
        Returns every consent record for a user, most recent
        first. Useful for support/legal requests ("show me
        every time this user overrode an allergen warning").
        """
        return (
            self.db.query(AllergenOverrideConsent)
            .filter(AllergenOverrideConsent.user_id == user_id)
            .order_by(AllergenOverrideConsent.confirmed_at.desc())
            .all()
        )

    def get_by_recipe(self, recipe_id: uuid.UUID) -> Optional[AllergenOverrideConsent]:
        """
        Returns the consent record tied to a specific recipe,
        if one exists (a recipe only ever has zero or one —
        it's created once, at the moment the recipe itself
        is saved).
        """
        return (
            self.db.query(AllergenOverrideConsent)
            .filter(AllergenOverrideConsent.recipe_id == recipe_id)
            .first()
        )

    # ---------------------------------------------------
    # Create — the ONLY write operation this repository
    # supports. See module docstring.
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        recipe_id: uuid.UUID,
        user_email_snapshot: str,
        user_name_snapshot: str,
        recipe_title_snapshot: str,
        flagged_allergens: List[str],
        warning_text_shown: str,
    ) -> AllergenOverrideConsent:
        consent = AllergenOverrideConsent(
            user_id=user_id,
            recipe_id=recipe_id,
            user_email_snapshot=user_email_snapshot,
            user_name_snapshot=user_name_snapshot,
            recipe_title_snapshot=recipe_title_snapshot,
            flagged_allergens=flagged_allergens,
            warning_text_shown=warning_text_shown,
        )

        self.db.add(consent)
        self.db.commit()
        self.db.refresh(consent)

        return consent