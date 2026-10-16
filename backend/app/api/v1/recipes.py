"""
=========================================================
AIMeals Backend
Recipe API Routes

Endpoints:
    POST   /api/v1/recipes                 - create a manually-authored recipe
    GET    /api/v1/recipes/mine            - list the current user's own recipes
    GET    /api/v1/recipes/system          - list system/curated recipes
    GET    /api/v1/recipes/{recipe_id}      - get a single recipe by id
    PATCH  /api/v1/recipes/{recipe_id}      - partial update (owner only)
    DELETE /api/v1/recipes/{recipe_id}      - delete (owner only)

All endpoints require a valid access token (Authorization: Bearer <token>).

Notes:
    - /mine and /system are declared BEFORE /{recipe_id} —
      FastAPI matches routes in declaration order, so a
      static path segment must come before a path-parameter
      route it could otherwise be mistaken for.
    - This is CRUD only. Recipe GENERATION (via Claude) is a
      separate AI route, built later in Phase 9.

Dependencies:
    - app.controller.recipe_controller.RecipeController
    - app.core.dependencies.get_current_user
    - app.B_database.get_db
=========================================================
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.controller.recipe_controller import RecipeController
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.recipe import RecipeCreate, RecipeOut, RecipeUpdate

router = APIRouter(prefix="/api/v1/recipes", tags=["Recipes"])


# =========================================================
# Create Recipe
# =========================================================

@router.post(
    "",
    response_model=RecipeOut,
    status_code=status.HTTP_201_CREATED,
)
def create_recipe(
    payload: RecipeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeOut:
    """
    Creates a manually-authored recipe owned by the current user.
    """
    controller = RecipeController(db)
    return controller.create_recipe(current_user.id, payload)


# =========================================================
# List My Recipes
# =========================================================

@router.get(
    "/mine",
    response_model=List[RecipeOut],
    status_code=status.HTTP_200_OK,
)
def get_my_recipes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RecipeOut]:
    """
    Returns every recipe created by the current user (manual
    or AI-generated).
    """
    controller = RecipeController(db)
    return controller.get_user_recipes(current_user.id)


# =========================================================
# List System Recipes
# =========================================================

@router.get(
    "/system",
    response_model=List[RecipeOut],
    status_code=status.HTTP_200_OK,
)
def get_system_recipes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RecipeOut]:
    """
    Returns system/curated recipes (created_by_user_id is
    null) — shared across all users.
    """
    controller = RecipeController(db)
    return controller.get_system_recipes()


# =========================================================
# Get Single Recipe
# =========================================================

@router.get(
    "/{recipe_id}",
    response_model=RecipeOut,
    status_code=status.HTTP_200_OK,
)
def get_recipe(
    recipe_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeOut:
    """
    Returns a single recipe by id. Unlike GET /profile, a
    missing id here IS a 404 — this is a direct single-resource
    fetch, not a "do you have one yet" check.
    """
    controller = RecipeController(db)
    recipe = controller.get_recipe(recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recipe found with id {recipe_id}.",
        )

    return recipe


# =========================================================
# Update Recipe
# =========================================================

@router.patch(
    "/{recipe_id}",
    response_model=RecipeOut,
    status_code=status.HTTP_200_OK,
)
def update_recipe(
    recipe_id: uuid.UUID,
    payload: RecipeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeOut:
    """
    Partially updates a recipe. Only fields included in the
    request body are changed.

    Returns 404 if no such recipe exists, 403 if it belongs
    to another user or is a system recipe.
    """
    controller = RecipeController(db)
    return controller.update_recipe(recipe_id, current_user.id, payload)


# =========================================================
# Delete Recipe
# =========================================================

@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_recipe(
    recipe_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Deletes a recipe.

    Returns 404 if no such recipe exists, 403 if it belongs
    to another user or is a system recipe.
    """
    controller = RecipeController(db)
    controller.delete_recipe(recipe_id, current_user.id)