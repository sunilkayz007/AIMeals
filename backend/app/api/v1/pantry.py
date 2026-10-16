"""
=========================================================
AIMeals Backend
Pantry API Routes

Endpoints:
    POST   /api/v1/pantry                        - add a pantry item batch
    GET    /api/v1/pantry                         - list all of the current user's pantry items
    GET    /api/v1/pantry/expiring-soon           - items expiring within N days (default 3)
    PATCH  /api/v1/pantry/{item_id}                - partial update of a pantry item
    DELETE /api/v1/pantry/{item_id}                - remove a pantry item

All endpoints require a valid access token (Authorization: Bearer <token>).

Dependencies:
    - app.controller.pantry_controller.PantryController
    - app.core.dependencies.get_current_user
    - app.B_database.get_db
=========================================================
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.controller.pantry_controller import PantryController
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.pantry import PantryItemCreate, PantryItemOut, PantryItemUpdate

router = APIRouter(prefix="/api/v1/pantry", tags=["Pantry"])


# =========================================================
# Add Pantry Item
# =========================================================

@router.post(
    "",
    response_model=PantryItemOut,
    status_code=status.HTTP_201_CREATED,
)
def add_item(
    payload: PantryItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PantryItemOut:
    """
    Adds a new pantry item batch. Always creates a new row —
    does not merge with an existing item of the same name, by
    design (supports per-batch expiration tracking).
    """
    controller = PantryController(db)
    return controller.add_item(current_user.id, payload)


# =========================================================
# List Pantry
# =========================================================

@router.get(
    "",
    response_model=List[PantryItemOut],
    status_code=status.HTTP_200_OK,
)
def get_user_pantry(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PantryItemOut]:
    """
    Returns every pantry item batch belonging to the current user.
    """
    controller = PantryController(db)
    return controller.get_user_pantry(current_user.id)


# =========================================================
# Expiring Soon
# =========================================================

@router.get(
    "/expiring-soon",
    response_model=List[PantryItemOut],
    status_code=status.HTTP_200_OK,
)
def get_expiring_soon(
    within_days: int = Query(default=3, ge=1, description="Items expiring within this many days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PantryItemOut]:
    """
    Returns pantry items expiring within the given number of
    days (default 3) — the same query Pantry Chef uses to
    prioritize ingredients.
    """
    controller = PantryController(db)
    return controller.get_expiring_soon(current_user.id, within_days)


# =========================================================
# Update Pantry Item
# =========================================================

@router.patch(
    "/{item_id}",
    response_model=PantryItemOut,
    status_code=status.HTTP_200_OK,
)
def update_item(
    item_id: uuid.UUID,
    payload: PantryItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PantryItemOut:
    """
    Partially updates a pantry item (e.g. adjusting quantity
    after some is used). Only fields included in the request
    body are changed.

    Returns 404 if no such item exists, 403 if it belongs to
    another user.
    """
    controller = PantryController(db)
    return controller.update_item(item_id, current_user.id, payload)


# =========================================================
# Remove Pantry Item
# =========================================================

@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Removes a pantry item entirely (e.g. fully used up or expired).

    Returns 404 if no such item exists, 403 if it belongs to
    another user.
    """
    controller = PantryController(db)
    controller.remove_item(item_id, current_user.id)