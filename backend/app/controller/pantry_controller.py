"""
=========================================================
AIMeals Backend
Pantry Controller

Responsibilities:
    - Orchestrate calls to PantryService
    - Translate framework-agnostic service exceptions into
      HTTPException with correct status codes
    - Convert SQLAlchemy models into Pydantic response schemas

Dependencies:
    - app.services.pantry_service.PantryService
    - app.core.exceptions

Notes:
    - Controllers contain NO business logic. They orchestrate
      and translate only.
    - update_item() calls payload.model_dump(exclude_unset=True)
      before passing fields to the service, since
      PantryService.update_item() passes **fields straight
      through to the repository without filtering unset ones
      itself — see PantryItemUpdate's schema docstring.
=========================================================
"""

import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotPantryItemOwnerError, PantryItemNotFoundError
from app.schemas.pantry import PantryItemCreate, PantryItemOut, PantryItemUpdate
from app.services.pantry_service import PantryService


# =========================================================
# Pantry Controller
# =========================================================

class PantryController:
    """
    Thin orchestration layer between API routes and PantryService.
    """

    def __init__(self, db: Session):
        self.service = PantryService(db)

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def add_item(self, user_id: uuid.UUID, payload: PantryItemCreate) -> PantryItemOut:
        item = self.service.add_item(
            user_id=user_id,
            ingredient_name=payload.ingredient_name,
            quantity=payload.quantity,
            unit=payload.unit,
            expiration_date=payload.expiration_date,
        )
        return PantryItemOut.model_validate(item)

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_user_pantry(self, user_id: uuid.UUID) -> List[PantryItemOut]:
        items = self.service.get_user_pantry(user_id)
        return [PantryItemOut.model_validate(item) for item in items]

    def get_expiring_soon(self, user_id: uuid.UUID, within_days: int) -> List[PantryItemOut]:
        items = self.service.get_expiring_soon(user_id, within_days=within_days)
        return [PantryItemOut.model_validate(item) for item in items]

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update_item(
        self,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: PantryItemUpdate,
    ) -> PantryItemOut:
        fields = payload.model_dump(exclude_unset=True)

        try:
            item = self.service.update_item(item_id, user_id, **fields)
        except PantryItemNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotPantryItemOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )

        return PantryItemOut.model_validate(item)

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def remove_item(self, item_id: uuid.UUID, user_id: uuid.UUID) -> None:
        try:
            self.service.remove_item(item_id, user_id)
        except PantryItemNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotPantryItemOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )