"""
=========================================================
AIMeals Backend
Nutrition Log Controller

Responsibilities:
    - Orchestrate calls to NutritionLogService
    - Translate framework-agnostic service exceptions into
      HTTPException with correct status codes
    - Convert SQLAlchemy models into Pydantic response schemas

Dependencies:
    - app.services.nutrition_log_service.NutritionLogService
    - app.core.exceptions
=========================================================
"""

import uuid
from datetime import date
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    FoodImageNotConfirmedError,
    FoodImageNotFoundError,
    NotFoodImageOwnerError,
    NotLogOwnerError,
    NutritionLogNotFoundError,
    RecipeNotFoundError,
)
from app.schemas.nutrition_log import (
    DailyTotalsOut,
    NutritionLogCreate,
    NutritionLogFromFoodImageCreate,
    NutritionLogFromRecipeCreate,
    NutritionLogOut,
    NutritionLogUpdate,
    PendingConfirmationOut,
)
from app.services.nutrition_log_service import NutritionLogService


# =========================================================
# Nutrition Log Controller
# =========================================================

class NutritionLogController:
    """
    Thin orchestration layer between API routes and NutritionLogService.
    """

    def __init__(self, db: Session):
        self.service = NutritionLogService(db)

    # ---------------------------------------------------
    # Create — Manual Entry
    # ---------------------------------------------------

    def log_meal(self, user_id: uuid.UUID, payload: NutritionLogCreate) -> NutritionLogOut:
        log = self.service.log_meal(
            user_id=user_id,
            logged_at=payload.logged_at,
            meal_type=payload.meal_type,
            food_name=payload.food_name,
            calories=payload.calories,
            protein_g=payload.protein_g,
            carbs_g=payload.carbs_g,
            fat_g=payload.fat_g,
            fiber_g=payload.fiber_g,
            water_ml=payload.water_ml,
            micronutrients=payload.micronutrients,
            recipe_id=payload.recipe_id,
            notes=payload.notes,
        )
        return NutritionLogOut.model_validate(log)

    # ---------------------------------------------------
    # Create — From Recipe
    # ---------------------------------------------------

    def log_meal_from_recipe(
        self,
        user_id: uuid.UUID,
        payload: NutritionLogFromRecipeCreate,
    ) -> NutritionLogOut:
        try:
            log = self.service.log_meal_from_recipe(
                user_id=user_id,
                logged_at=payload.logged_at,
                meal_type=payload.meal_type,
                recipe_id=payload.recipe_id,
                portion_percentage=payload.portion_percentage,
                notes=payload.notes,
            )
        except RecipeNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        return NutritionLogOut.model_validate(log)

    # ---------------------------------------------------
    # Create — From Food Image Scan
    # ---------------------------------------------------

    def log_meal_from_food_image(
        self,
        user_id: uuid.UUID,
        payload: NutritionLogFromFoodImageCreate,
    ) -> NutritionLogOut:
        try:
            log = self.service.log_meal_from_food_image(
                user_id=user_id,
                logged_at=payload.logged_at,
                meal_type=payload.meal_type,
                food_image_id=payload.food_image_id,
                portion_percentage=payload.portion_percentage,
                notes=payload.notes,
            )
        except FoodImageNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotFoodImageOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        except FoodImageNotConfirmedError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

        return NutritionLogOut.model_validate(log)

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_logs_for_day(self, user_id: uuid.UUID, target_date: date) -> List[NutritionLogOut]:
        logs = self.service.get_logs_for_day(user_id, target_date)
        return [NutritionLogOut.model_validate(log) for log in logs]

    def get_logs_for_range(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> List[NutritionLogOut]:
        logs = self.service.get_logs_for_range(user_id, start_date, end_date)
        return [NutritionLogOut.model_validate(log) for log in logs]

    def get_daily_totals(self, user_id: uuid.UUID, target_date: date) -> DailyTotalsOut:
        totals = self.service.get_daily_totals(user_id, target_date)
        return DailyTotalsOut(**totals)

    # ---------------------------------------------------
    # Pending Meal Confirmations
    # ---------------------------------------------------

    def get_pending_confirmations(self, user_id: uuid.UUID) -> List[PendingConfirmationOut]:
        pending = self.service.get_pending_confirmations(user_id)
        return [PendingConfirmationOut(**item) for item in pending]

    def dismiss_pending_confirmation(
        self,
        user_id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
    ) -> None:
        self.service.dismiss_pending_confirmation(user_id, source_type, source_id)

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update_log(
        self,
        log_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: NutritionLogUpdate,
    ) -> NutritionLogOut:
        fields = payload.model_dump(exclude_unset=True)

        try:
            log = self.service.update_log(log_id, user_id, **fields)
        except NutritionLogNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotLogOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )

        return NutritionLogOut.model_validate(log)

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete_log(self, log_id: uuid.UUID, user_id: uuid.UUID) -> None:
        try:
            self.service.delete_log(log_id, user_id)
        except NutritionLogNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotLogOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )