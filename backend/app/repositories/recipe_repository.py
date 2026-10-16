"""
=========================================================
AIMeals Backend
Recipe Repository

Responsibilities:
    - Perform CRUD operations against the recipes table
    - Contains NO business logic

Dependencies:
    - app.models.recipe.Recipe

Notes:
    - Hard delete is used here (not soft-deactivation).
      This is safe because NutritionLog.recipe_id and
      Meal.recipe_id both use ON DELETE SET NULL — deleting
      a recipe detaches it from historical records rather
      than breaking them.

Example usage:
    from app.repositories.recipe_repository import RecipeRepository

    repo = RecipeRepository(db)
    system_recipes = repo.get_system_recipes()
=========================================================
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.recipe import Recipe


# =========================================================
# Recipe Repository
# =========================================================

class RecipeRepository:
    """
    Encapsulates all direct database access for the Recipe model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_id(self, recipe_id: uuid.UUID) -> Optional[Recipe]:
        return self.db.query(Recipe).filter(Recipe.id == recipe_id).first()

    def get_by_user(self, user_id: uuid.UUID) -> List[Recipe]:
        """Returns all recipes created/saved by a specific user."""
        return (
            self.db.query(Recipe)
            .filter(Recipe.created_by_user_id == user_id)
            .order_by(Recipe.created_at.desc())
            .all()
        )

    def get_system_recipes(self) -> List[Recipe]:
        """Returns the curated recipe library (not tied to any user)."""
        return (
            self.db.query(Recipe)
            .filter(Recipe.created_by_user_id.is_(None))
            .order_by(Recipe.title)
            .all()
        )

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        title: str,
        instructions: str,
        ingredients: str,
        created_by_user_id: Optional[uuid.UUID] = None,
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
        micronutrients: Optional[dict] = None,
        is_ai_generated: bool = False,
        contains_allergen: bool = False,
        flagged_allergens: Optional[List[str]] = None,
    ) -> Recipe:
        new_recipe = Recipe(
            created_by_user_id=created_by_user_id,
            title=title,
            description=description,
            instructions=instructions,
            ingredients=ingredients,
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
            contains_allergen=contains_allergen,
            flagged_allergens=flagged_allergens,
        )

        self.db.add(new_recipe)
        self.db.commit()
        self.db.refresh(new_recipe)

        return new_recipe

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update(self, recipe: Recipe, **fields) -> Recipe:
        """
        Updates arbitrary fields on an existing recipe.

        Usage:
            repo.update(recipe, title="New Title", servings=4)
        """
        for key, value in fields.items():
            setattr(recipe, key, value)

        self.db.commit()
        self.db.refresh(recipe)

        return recipe

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete(self, recipe: Recipe) -> None:
        """
        Permanently deletes a recipe. Safe due to
        ON DELETE SET NULL on referencing tables.
        """
        self.db.delete(recipe)
        self.db.commit()
