"""
=========================================================
AIMeals Backend
Pantry Schemas

Responsibilities:
    - Define request/response shapes for pantry item data

Example usage:
    from app.schemas.pantry import PantryItemCreate, PantryItemOut

    def add_item(payload: PantryItemCreate):
        ...
=========================================================
"""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


# =========================================================
# Request Schema — Add Pantry Item
# =========================================================

class PantryItemCreate(BaseModel):
    """
    Shape of the payload accepted by POST /pantry.

    Deliberately always CREATES a new row, even if an item
    with the same ingredient_name already exists — matches
    PantryItem's multi-batch design (e.g. two separate Eggs
    batches with different expiration dates), so the client
    should never try to "merge" quantities client-side.
    """

    ingredient_name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiration_date: Optional[date] = None

    @field_validator("ingredient_name")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("ingredient_name cannot be blank.")
        return value.strip()


# =========================================================
# Request Schema — Update Pantry Item
# =========================================================

class PantryItemUpdate(BaseModel):
    """
    Shape of the payload accepted by PATCH /pantry/{item_id}.

    All fields optional. Unlike ProfileUpdate, PantryService.update_item()
    does NOT filter out unset fields itself — it passes **fields
    straight through to the repository. The controller is
    responsible for only including fields the client actually
    set (via payload.model_dump(exclude_unset=True)), so an
    omitted field is left untouched rather than overwritten
    with null.
    """

    ingredient_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiration_date: Optional[date] = None

    @field_validator("ingredient_name")
    @classmethod
    def validate_not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("ingredient_name cannot be blank.")
        return value.strip() if value is not None else value


# =========================================================
# Response Schema — Pantry Item
# =========================================================

class PantryItemOut(BaseModel):
    """
    Shape of pantry item data returned to the client.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    ingredient_name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiration_date: Optional[date] = None
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)