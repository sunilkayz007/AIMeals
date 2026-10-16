"""
=========================================================
AIMeals Backend
Pantry Service

Responsibilities:
    - Orchestrate pantry item creation/management
    - Enforce ownership on edits/deletes

Dependencies:
    - app.repositories.pantry_item_repository.PantryItemRepository
    - app.core.exceptions

Example usage:
    from app.services.pantry_service import PantryService

    service = PantryService(db)
    service.add_item(user.id, "Eggs", quantity=12, unit="pieces", expiration_date=exp)
    expiring = service.get_expiring_soon(user.id, within_days=3)
=========================================================
"""

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotPantryItemOwnerError, PantryItemNotFoundError
from app.models.pantry_item import PantryItem
from app.repositories.pantry_item_repository import PantryItemRepository


# =========================================================
# Pantry Service
# =========================================================

class PantryService:
    """
    Contains the business logic for pantry item management.
    """

    def __init__(self, db: Session):
        self.db = db
        self.pantry_repo = PantryItemRepository(db)

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def add_item(
        self,
        user_id: uuid.UUID,
        ingredient_name: str,
        quantity: Optional[float] = None,
        unit: Optional[str] = None,
        expiration_date: Optional[date] = None,
    ) -> PantryItem:
        """
        Adds a new pantry item batch. Deliberately does NOT
        merge with existing rows of the same ingredient — see
        the PantryItem model's design notes: multiple rows
        per ingredient are intentional, to support accurate
        per-batch expiration tracking.
        """
        return self.pantry_repo.create(
            user_id=user_id,
            ingredient_name=ingredient_name,
            quantity=quantity,
            unit=unit,
            expiration_date=expiration_date,
        )

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_user_pantry(self, user_id: uuid.UUID) -> List[PantryItem]:
        return self.pantry_repo.get_by_user(user_id)

    def get_expiring_soon(
        self,
        user_id: uuid.UUID,
        within_days: int = 3,
    ) -> List[PantryItem]:
        return self.pantry_repo.get_expiring_soon(user_id, within_days=within_days)

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update_item(self, item_id: uuid.UUID, user_id: uuid.UUID, **fields) -> PantryItem:
        """
        Updates a pantry item (e.g. adjusting quantity after
        some is used), enforcing ownership.

        Raises:
            PantryItemNotFoundError, NotPantryItemOwnerError
        """
        item = self._get_owned_item_or_raise(item_id, user_id)
        return self.pantry_repo.update(item, **fields)

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def remove_item(self, item_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Removes a pantry item entirely (e.g. it's been fully
        used up or has expired), enforcing ownership.
        """
        item = self._get_owned_item_or_raise(item_id, user_id)
        self.pantry_repo.delete(item)

    # ---------------------------------------------------
    # Internal Helper
    # ---------------------------------------------------

    def _get_owned_item_or_raise(self, item_id: uuid.UUID, user_id: uuid.UUID) -> PantryItem:
        item = self.pantry_repo.get_by_id(item_id)

        if item is None:
            raise PantryItemNotFoundError(f"No pantry item found with id {item_id}.")

        if item.user_id != user_id:
            raise NotPantryItemOwnerError("This pantry item belongs to another user.")

        return item