"""
=========================================================
AIMeals Backend
Meal Confirmation Dismissal Repository

Responsibilities:
    - Insert and look up meal_confirmation_dismissals rows
    - Contains NO business logic

Dependencies:
    - app.models.meal_confirmation_dismissal.MealConfirmationDismissal

Notes:
    - No update() method — a dismissal is a one-time fact,
      never edited after creation. No delete() either — there's
      no product reason to "un-dismiss" something; if the user
      changes their mind, they can just log the meal manually.

Example usage:
    from app.repositories.meal_confirmation_dismissal_repository import (
        MealConfirmationDismissalRepository,
    )

    repo = MealConfirmationDismissalRepository(db)
    repo.create(user_id=user.id, recipe_id=recipe.id)
=========================================================
"""

import uuid
from typing import Optional, Set

from sqlalchemy.orm import Session

from app.models.meal_confirmation_dismissal import MealConfirmationDismissal


# =========================================================
# Meal Confirmation Dismissal Repository
# =========================================================

class MealConfirmationDismissalRepository:
    """
    Encapsulates all direct database access for the
    MealConfirmationDismissal model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_dismissed_recipe_ids(self, user_id: uuid.UUID) -> Set[uuid.UUID]:
        rows = (
            self.db.query(MealConfirmationDismissal.recipe_id)
            .filter(
                MealConfirmationDismissal.user_id == user_id,
                MealConfirmationDismissal.recipe_id.isnot(None),
            )
            .distinct()
            .all()
        )
        return {row[0] for row in rows}

    def get_dismissed_food_image_ids(self, user_id: uuid.UUID) -> Set[uuid.UUID]:
        rows = (
            self.db.query(MealConfirmationDismissal.food_image_id)
            .filter(
                MealConfirmationDismissal.user_id == user_id,
                MealConfirmationDismissal.food_image_id.isnot(None),
            )
            .distinct()
            .all()
        )
        return {row[0] for row in rows}

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        recipe_id: Optional[uuid.UUID] = None,
        food_image_id: Optional[uuid.UUID] = None,
    ) -> MealConfirmationDismissal:
        dismissal = MealConfirmationDismissal(
            user_id=user_id,
            recipe_id=recipe_id,
            food_image_id=food_image_id,
        )

        self.db.add(dismissal)
        self.db.commit()
        self.db.refresh(dismissal)

        return dismissal