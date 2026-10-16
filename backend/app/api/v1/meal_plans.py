"""
=========================================================
AIMeals Backend
Meal Plan API Routes

Endpoints:
    POST   /api/v1/meal-plans                       - create a meal plan
    GET    /api/v1/meal-plans                        - list the current user's plans
    GET    /api/v1/meal-plans/meals/week              - planned meals across ALL plans in a date range
    DELETE /api/v1/meal-plans/meals/{meal_id}          - remove a single meal from its plan
    GET    /api/v1/meal-plans/{plan_id}                - get a single plan
    DELETE /api/v1/meal-plans/{plan_id}                - delete a plan (and its meals, via cascade)
    POST   /api/v1/meal-plans/{plan_id}/meals          - add a meal to a plan
    GET    /api/v1/meal-plans/{plan_id}/meals          - list meals in a plan

All endpoints require a valid access token (Authorization: Bearer <token>).

Notes:
    - No PATCH/update endpoints — MealPlanService has no
      update_plan()/update_meal() methods (create/read/delete
      only for both). Not inventing update logic here.
    - This is CRUD only. Meal plan GENERATION (via Claude) is
      a separate AI route, built later in Phase 9.

Dependencies:
    - app.controller.meal_plan_controller.MealPlanController
    - app.core.dependencies.get_current_user
    - app.B_database.get_db
=========================================================
"""

import uuid
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.controller.meal_plan_controller import MealPlanController
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.meal_plan import MealCreate, MealOut, MealPlanCreate, MealPlanOut

router = APIRouter(prefix="/api/v1/meal-plans", tags=["Meal Plans"])


# =========================================================
# Create Plan
# =========================================================

@router.post(
    "",
    response_model=MealPlanOut,
    status_code=status.HTTP_201_CREATED,
)
def create_plan(
    payload: MealPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MealPlanOut:
    """
    Creates a new meal plan container for the current user.
    """
    controller = MealPlanController(db)
    return controller.create_plan(current_user.id, payload)


# =========================================================
# List My Plans
# =========================================================

@router.get(
    "",
    response_model=List[MealPlanOut],
    status_code=status.HTTP_200_OK,
)
def get_my_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MealPlanOut]:
    """
    Returns every meal plan belonging to the current user.
    """
    controller = MealPlanController(db)
    return controller.get_user_plans(current_user.id)


# =========================================================
# Meals For a Week (across all plans)
# =========================================================

@router.get(
    "/meals/week",
    response_model=List[MealOut],
    status_code=status.HTTP_200_OK,
)
def get_meals_for_week(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MealOut]:
    """
    Returns the current user's planned meals across ALL of
    their plans within a date range — the query a weekly
    calendar view would actually use, since meals may span
    multiple overlapping plans.
    """
    controller = MealPlanController(db)
    return controller.get_meals_for_week(current_user.id, start_date, end_date)


# =========================================================
# Remove a Single Meal
# =========================================================

@router.delete(
    "/meals/{meal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_meal(
    meal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Removes a single meal from its plan, without deleting the
    whole plan. Ownership is enforced via the meal's parent
    plan.

    Returns 404 if no such meal exists, 403 if its parent
    plan belongs to another user.
    """
    controller = MealPlanController(db)
    controller.remove_meal(meal_id, current_user.id)


# =========================================================
# Get Single Plan
# =========================================================

@router.get(
    "/{plan_id}",
    response_model=MealPlanOut,
    status_code=status.HTTP_200_OK,
)
def get_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MealPlanOut:
    """
    Returns a single meal plan by id.
    """
    controller = MealPlanController(db)
    plan = controller.get_plan(plan_id)

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No meal plan found with id {plan_id}.",
        )

    return plan


# =========================================================
# Delete Plan
# =========================================================

@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Deletes a meal plan and, via cascade, all of its meals.

    Returns 404 if no such plan exists, 403 if it belongs to
    another user.
    """
    controller = MealPlanController(db)
    controller.delete_plan(plan_id, current_user.id)


# =========================================================
# Add Meal to Plan
# =========================================================

@router.post(
    "/{plan_id}/meals",
    response_model=MealOut,
    status_code=status.HTTP_201_CREATED,
)
def add_meal(
    plan_id: uuid.UUID,
    payload: MealCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MealOut:
    """
    Adds a meal to a plan. The plan must belong to the current
    user.

    Returns 404 if no such plan exists, 403 if it belongs to
    another user.
    """
    controller = MealPlanController(db)
    return controller.add_meal(plan_id, current_user.id, payload)


# =========================================================
# List Meals In a Plan
# =========================================================

@router.get(
    "/{plan_id}/meals",
    response_model=List[MealOut],
    status_code=status.HTTP_200_OK,
)
def get_meals_in_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MealOut]:
    """
    Returns every meal scheduled within a single plan.
    """
    controller = MealPlanController(db)
    return controller.get_meals_in_plan(plan_id)