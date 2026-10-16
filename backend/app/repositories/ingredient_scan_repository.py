"""
=========================================================
AIMeals Backend
Ingredient Scan Repository

Responsibilities:
    - Perform CRUD operations against the ingredient_scans table
    - Contains NO business logic (ownership checks, correction
      merging, etc. belong in the service layer)

Dependencies:
    - app.models.ingredient_scan.IngredientScan

Example usage:
    from app.repositories.ingredient_scan_repository import IngredientScanRepository

    repo = IngredientScanRepository(db)
    scan = repo.create(user_id=user.id, ingredients=[...])
=========================================================
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.ingredient_scan import IngredientScan, IngredientScanStatus


# =========================================================
# Ingredient Scan Repository
# =========================================================

class IngredientScanRepository:
    """
    Encapsulates all direct database access for the IngredientScan model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_id(self, scan_id: uuid.UUID) -> Optional[IngredientScan]:
        return self.db.query(IngredientScan).filter(IngredientScan.id == scan_id).first()

    def get_by_user(self, user_id: uuid.UUID, limit: Optional[int] = None) -> List[IngredientScan]:
        """
        Returns a user's own scans, most recent first. Used for
        the "recent scans" list on the Ingredient Scan screen —
        no ownership filtering needed elsewhere since the query
        is already scoped to user_id.
        """
        query = (
            self.db.query(IngredientScan)
            .filter(IngredientScan.user_id == user_id)
            .order_by(IngredientScan.created_at.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def get_expired(self, cutoff_time: datetime) -> List[IngredientScan]:
        """
        Returns ALL scans (regardless of status) created before
        cutoff_time. Used by the TTL cleanup script.

        Per project decision, confirmed scans are swept on the
        same 24h timer as abandoned pending ones — neither is
        needed once the window has passed, since a confirmed
        scan has already been consumed by generate_recipe_from_scan().
        """
        return (
            self.db.query(IngredientScan)
            .filter(IngredientScan.created_at < cutoff_time)
            .order_by(IngredientScan.created_at)
            .all()
        )

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        ingredients: list,
        ai_interaction_id: Optional[uuid.UUID] = None,
    ) -> IngredientScan:
        new_scan = IngredientScan(
            user_id=user_id,
            ingredients=ingredients,
            ai_interaction_id=ai_interaction_id,
            status=IngredientScanStatus.PENDING,
        )

        self.db.add(new_scan)
        self.db.commit()
        self.db.refresh(new_scan)

        return new_scan

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update(self, scan: IngredientScan, **fields) -> IngredientScan:
        for key, value in fields.items():
            setattr(scan, key, value)

        self.db.commit()
        self.db.refresh(scan)

        return scan

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete(self, scan: IngredientScan) -> None:
        self.db.delete(scan)
        self.db.commit()