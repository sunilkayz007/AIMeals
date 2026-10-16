"""
=========================================================
AIMeals Backend
Recipe Controller

Responsibilities:
    - Orchestrate calls to RecipeService
    - Translate framework-agnostic service exceptions into
      HTTPException with correct status codes
    - Convert SQLAlchemy models into Pydantic response schemas

Dependencies:
    - app.services.recipe_service.RecipeService
    - app.core.exceptions

Notes:
    - create_recipe() always creates a user-owned,
      is_ai_generated=False recipe — matches
      RecipeService.create_recipe()'s own design (it has no
      path to create a system recipe or mark one as
      AI-generated; those happen elsewhere).
    - get_recipe() returns None (not 404) when the id
      doesn't exist — the ROUTE decides whether that becomes
      a 404, since a single-item fetch by id is a different
      case from "no profile yet" (see profile_controller.py).
    - update_recipe()/delete_recipe() rely on
      RecipeService's ownership enforcement, which also
      blocks editing system recipes (created_by_user_id is
      None) even by an admin, through this service.
=========================================================
"""

import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotRecipeOwnerError, RecipeNotFoundError
from app.schemas.recipe import RecipeCreate, RecipeOut, RecipeUpdate
from app.services.recipe_service import RecipeService


# =========================================================
# Recipe Controller
# =========================================================

class RecipeController:
    """
    Thin orchestration layer between API routes and RecipeService.
    """

    def __init__(self, db: Session):
        self.service = RecipeService(db)

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create_recipe(self, user_id: uuid.UUID, payload: RecipeCreate) -> RecipeOut:
        recipe = self.service.create_recipe(
            user_id=user_id,
            title=payload.title,
            instructions=payload.instructions,
            ingredients=payload.ingredients,
            description=payload.description,
            prep_time_minutes=payload.prep_time_minutes,
            cook_time_minutes=payload.cook_time_minutes,
            servings=payload.servings,
            calories_per_serving=payload.calories_per_serving,
            protein_g=payload.protein_g,
            carbs_g=payload.carbs_g,
            fat_g=payload.fat_g,
            # FIXED Sep 2 2026 — these three were already accepted
            # by RecipeCreate but never forwarded past this
            # controller, so manually-created recipes silently
            # lost fiber/water/micronutrient data. See
            # RecipeService.create_recipe()'s docstring for the
            # full trace.
            fiber_g_per_serving=payload.fiber_g_per_serving,
            water_ml_per_serving=payload.water_ml_per_serving,
            micronutrients=payload.micronutrients,
            # is_ai_generated intentionally omitted — defaults
            # to False in the service. This endpoint is for
            # manually-authored recipes only.
        )
        return RecipeOut.model_validate(recipe)

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_recipe(self, recipe_id: uuid.UUID) -> Optional[RecipeOut]:
        recipe = self.service.get_recipe(recipe_id)
        if recipe is None:
            return None
        return RecipeOut.model_validate(recipe)

    def get_user_recipes(self, user_id: uuid.UUID) -> List[RecipeOut]:
        recipes = self.service.get_user_recipes(user_id)
        return [RecipeOut.model_validate(r) for r in recipes]

    def get_system_recipes(self) -> List[RecipeOut]:
        recipes = self.service.get_system_recipes()
        return [RecipeOut.model_validate(r) for r in recipes]

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update_recipe(
        self,
        recipe_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: RecipeUpdate,
    ) -> RecipeOut:
        fields = payload.model_dump(exclude_unset=True)

        try:
            recipe = self.service.update_recipe(recipe_id, user_id, **fields)
        except RecipeNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotRecipeOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )

        return RecipeOut.model_validate(recipe)

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete_recipe(self, recipe_id: uuid.UUID, user_id: uuid.UUID) -> None:
        try:
            self.service.delete_recipe(recipe_id, user_id)
        except RecipeNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except NotRecipeOwnerError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )