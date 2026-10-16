"""
=========================================================
AIMeals Backend
Food Image Repository

Responsibilities:
    - Perform CRUD operations against the food_images table
    - Contains NO business logic

Dependencies:
    - app.models.food_image.FoodImage

Example usage:
    from app.repositories.food_image_repository import FoodImageRepository

    repo = FoodImageRepository(db)
    scan = repo.get_by_id(image_id)
=========================================================
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.food_image import FoodImage, FoodImageStatus


# =========================================================
# Food Image Repository
# =========================================================

class FoodImageRepository:
    """
    Encapsulates all direct database access for the FoodImage
    model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_id(self, image_id: uuid.UUID) -> Optional[FoodImage]:
        return self.db.query(FoodImage).filter(FoodImage.id == image_id).first()

    def get_by_user(self, user_id: uuid.UUID, limit: Optional[int] = None) -> List[FoodImage]:
        query = (
            self.db.query(FoodImage)
            .filter(FoodImage.user_id == user_id)
            .order_by(FoodImage.uploaded_at.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        detected_foods: list[dict],
        ai_interaction_id: Optional[uuid.UUID] = None,
        image_url: Optional[str] = None,
        status: FoodImageStatus = FoodImageStatus.CONFIRMED,
        meal_type: Optional[str] = None,
        total_calories: Optional[float] = None,
        total_protein_g: Optional[float] = None,
        total_carbs_g: Optional[float] = None,
        total_fat_g: Optional[float] = None,
        total_fiber_g: Optional[float] = None,
        total_water_ml: Optional[float] = None,
        total_micronutrients: Optional[dict] = None,
    ) -> FoodImage:
        """
        Creates a new food image analysis row.
        """
        new_image = FoodImage(
            user_id=user_id,
            ai_interaction_id=ai_interaction_id,
            image_url=image_url,
            status=status,
            meal_type=meal_type,
            detected_foods=detected_foods,
            total_calories=total_calories,
            total_protein_g=total_protein_g,
            total_carbs_g=total_carbs_g,
            total_fat_g=total_fat_g,
            total_fiber_g=total_fiber_g,
            total_water_ml=total_water_ml,
            total_micronutrients=total_micronutrients,
        )

        self.db.add(new_image)
        self.db.commit()
        self.db.refresh(new_image)

        return new_image

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update(self, food_image: FoodImage, **fields) -> FoodImage:
        """
        Updates arbitrary fields on an existing food image row.

        Usage:
            repo.update(image, status=FoodImageStatus.CONFIRMED, total_calories=410)
        """
        for key, value in fields.items():
            setattr(food_image, key, value)

        self.db.commit()
        self.db.refresh(food_image)

        return food_image
