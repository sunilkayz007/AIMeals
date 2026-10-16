"""
=========================================================
AIMeals Backend
Pantry Item Repository

Responsibilities:
    - Perform CRUD operations against the pantry_items table
    - Contains NO business logic

Dependencies:
    - app.models.pantry_item.PantryItem

Example usage:
    from app.repositories.pantry_item_repository import PantryItemRepository

    repo = PantryItemRepository(db)
    expiring_soon = repo.get_expiring_soon(user.id, within_days=3)
=========================================================
"""

import uuid
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.pantry_item import PantryItem


# =========================================================
# Pantry Item Repository
# =========================================================

class PantryItemRepository:
    """
    Encapsulates all direct database access for the PantryItem model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_id(self, item_id: uuid.UUID) -> Optional[PantryItem]:
        return self.db.query(PantryItem).filter(PantryItem.id == item_id).first()

    def get_by_user(self, user_id: uuid.UUID) -> List[PantryItem]:
        return (
            self.db.query(PantryItem)
            .filter(PantryItem.user_id == user_id)
            .order_by(PantryItem.ingredient_name)
            .all()
        )

    def get_expiring_soon(
        self,
        user_id: uuid.UUID,
        within_days: int = 3,
    ) -> List[PantryItem]:
        """
        Returns a user's pantry items expiring within the
        given number of days (inclusive), ordered soonest
        first. Items with no expiration_date are excluded,
        since "expiring soon" doesn't apply to them.
        """
        cutoff = date.today() + timedelta(days=within_days)

        return (
            self.db.query(PantryItem)
            .filter(
                PantryItem.user_id == user_id,
                PantryItem.expiration_date.is_not(None),
                PantryItem.expiration_date <= cutoff,
            )
            .order_by(PantryItem.expiration_date)
            .all()
        )

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        ingredient_name: str,
        quantity: Optional[float] = None,
        unit: Optional[str] = None,
        expiration_date: Optional[date] = None,
    ) -> PantryItem:
        new_item = PantryItem(
            user_id=user_id,
            ingredient_name=ingredient_name,
            quantity=quantity,
            unit=unit,
            expiration_date=expiration_date,
        )

        self.db.add(new_item)
        self.db.commit()
        self.db.refresh(new_item)

        return new_item

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update(self, item: PantryItem, **fields) -> PantryItem:
        for key, value in fields.items():
            setattr(item, key, value)

        self.db.commit()
        self.db.refresh(item)

        return item

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete(self, item: PantryItem) -> None:
        self.db.delete(item)
        self.db.commit()