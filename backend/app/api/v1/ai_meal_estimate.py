"""
=========================================================
AIMeals Backend
AI Meal Nutrition Estimate API Route

Endpoint:
    POST /api/v1/ai/nutrition/estimate   - estimate nutrition
        for a user-typed food description, for the manual
        meal-log form's "Estimate with AI" button

Requires a valid access token (Authorization: Bearer <token>).

Notes:
    - NON-streamed — a single request/response, not SSE. See
      app/schemas/ai_meal_estimate.py's module docstring for
      why (a quick, cheap, single-turn call, not a multi-stage
      generation).
    - The response is never persisted server-side by this
      endpoint — it only pre-fills the manual meal-log form
      client-side. The user still explicitly submits the real
      log via the existing POST /nutrition-logs endpoint.

Dependencies:
    - app.services.ai_service.AIService
    - app.schemas.ai_meal_estimate.MealNutritionEstimateRequest / Response
    - app.core.dependencies.get_current_user
=========================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    ClaudeAPIError,
    InsufficientCreditsError,
    MealNutritionEstimateError,
)
from app.models.user import User
from app.schemas.ai_meal_estimate import (
    MealNutritionEstimateRequest,
    MealNutritionEstimateResponse,
)
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


@router.post(
    "/nutrition/estimate",
    response_model=MealNutritionEstimateResponse,
    status_code=status.HTTP_200_OK,
)
def estimate_meal_nutrition(
    payload: MealNutritionEstimateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MealNutritionEstimateResponse:
    """
    Estimates calories/protein/carbs/fat/fiber/water/
    micronutrients for a user-typed food description, to
    pre-fill the manual meal-log form. Costs 1 credit (see
    SubscriptionService.INTERACTION_CREDIT_COSTS).
    """
    service = AIService(db)

    try:
        estimate = service.estimate_meal_nutrition(
            user_id=current_user.id,
            food_name=payload.food_name,
            quantity_description=payload.quantity_description,
        )
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e),
        )
    except ClaudeAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI estimate failed: {e}",
        )
    except MealNutritionEstimateError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return MealNutritionEstimateResponse(**estimate)
