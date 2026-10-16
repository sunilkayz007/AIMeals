"""
=========================================================
AIMeals Backend
Recipe Service

Responsibilities:
    - Orchestrate recipe creation, retrieval, update, deletion
    - Enforce ownership rules: only a recipe's creator may
      edit or delete it; system recipes (created_by_user_id
      is None) cannot be edited or deleted by any regular
      user through this service

Dependencies:
    - app.repositories.recipe_repository.RecipeRepository
    - app.core.exceptions

Example usage:
    from app.services.recipe_service import RecipeService

    service = RecipeService(db)
    recipe = service.create_recipe(user.id, title="...", ...)
    service.update_recipe(recipe.id, user.id, servings=4)
=========================================================
"""

import uuid
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotRecipeOwnerError, RecipeNotFoundError
from app.models.recipe import Recipe
from app.repositories.recipe_repository import RecipeRepository


# =========================================================
# Recipe Service
# =========================================================

class RecipeService:
    """
    Contains the business logic for recipe management,
    primarily ownership enforcement.
    """

    def __init__(self, db: Session):
        self.db = db
        self.recipe_repo = RecipeRepository(db)

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_recipe(self, recipe_id: uuid.UUID) -> Optional[Recipe]:
        return self.recipe_repo.get_by_id(recipe_id)

    def get_user_recipes(self, user_id: uuid.UUID) -> List[Recipe]:
        return self.recipe_repo.get_by_user(user_id)

    def get_system_recipes(self) -> List[Recipe]:
        return self.recipe_repo.get_system_recipes()

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create_recipe(
        self,
        user_id: uuid.UUID,
        title: str,
        instructions: str,
        ingredients: str,
        description: Optional[str] = None,
        prep_time_minutes: Optional[int] = None,
        cook_time_minutes: Optional[int] = None,
        servings: int = 1,
        calories_per_serving: Optional[float] = None,
        protein_g: Optional[float] = None,
        carbs_g: Optional[float] = None,
        fat_g: Optional[float] = None,
        fiber_g_per_serving: Optional[float] = None,
        water_ml_per_serving: Optional[float] = None,
        micronutrients: Optional[Dict[str, float]] = None,
        is_ai_generated: bool = False,
    ) -> Recipe:
        """
        Creates a recipe owned by the given user. Regular
        users always create user-owned recipes through this
        method — system recipes (created_by_user_id=None)
        are a separate, deliberately unexposed path (e.g. an
        admin seeding script), not something this method
        supports, so ordinary users can never accidentally
        create an unowned recipe.

        fiber_g_per_serving / water_ml_per_serving /
        micronutrients: FIXED Sep 2 2026 — these were accepted
        by RecipeCreate (the request schema) and fully supported
        by RecipeRepository.create() and the Recipe model, but
        this method never accepted or forwarded them, so every
        manually-created recipe silently lost fiber/water/
        micronutrient data even when the client submitted it.
        update_recipe() was NOT affected (it forwards **fields
        generically via model_dump(), no fixed parameter list) —
        this bug was isolated to creation only.
        """
        return self.recipe_repo.create(
            title=title,
            instructions=instructions,
            ingredients=ingredients,
            created_by_user_id=user_id,
            description=description,
            prep_time_minutes=prep_time_minutes,
            cook_time_minutes=cook_time_minutes,
            servings=servings,
            calories_per_serving=calories_per_serving,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            fiber_g_per_serving=fiber_g_per_serving,
            water_ml_per_serving=water_ml_per_serving,
            micronutrients=micronutrients,
            is_ai_generated=is_ai_generated,
        )

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update_recipe(self, recipe_id: uuid.UUID, user_id: uuid.UUID, **fields) -> Recipe:
        """
        Updates a recipe, enforcing that only its creator
        may do so.

        Raises:
            RecipeNotFoundError: if no recipe exists with
                this id.
            NotRecipeOwnerError: if the recipe exists but
                belongs to someone else, OR is a system
                recipe (created_by_user_id is None) — system
                recipes are never editable through this
                service, regardless of who's asking.
        """
        recipe = self._get_owned_recipe_or_raise(recipe_id, user_id)
        return self.recipe_repo.update(recipe, **fields)

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete_recipe(self, recipe_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Deletes a recipe, enforcing the same ownership rule
        as update_recipe.

        Raises:
            RecipeNotFoundError, NotRecipeOwnerError: see
                update_recipe.
        """
        recipe = self._get_owned_recipe_or_raise(recipe_id, user_id)
        self.recipe_repo.delete(recipe)

    # ---------------------------------------------------
    # Internal Helper
    # ---------------------------------------------------

    def _get_owned_recipe_or_raise(self, recipe_id: uuid.UUID, user_id: uuid.UUID) -> Recipe:
        """
        Fetches a recipe and verifies the given user owns it.
        Shared by update_recipe and delete_recipe so the
        ownership check logic exists in exactly one place.
        """
        recipe = self.recipe_repo.get_by_id(recipe_id)

        if recipe is None:
            raise RecipeNotFoundError(f"No recipe found with id {recipe_id}.")

        if recipe.created_by_user_id != user_id:
            raise NotRecipeOwnerError(
                "This recipe cannot be modified: it either belongs to "
                "another user or is a system recipe."
            )

        return recipe