"""
=========================================================
AIMeals Backend
Subscription API Routes

Endpoints:
    GET /api/v1/subscription                                  - the current user's subscription/credit state
    GET /api/v1/subscription/credit-cost/{interaction_type}    - credit cost for a given AI interaction type

All endpoints require a valid access token (Authorization: Bearer <token>).

Notes:
    - Deliberately read-only for now — see subscription_controller.py
      for why tier upgrade/billing endpoints aren't exposed yet.

Dependencies:
    - app.controller.subscription_controller.SubscriptionController
    - app.core.dependencies.get_current_user
    - app.B_database.get_db
=========================================================
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.controller.subscription_controller import SubscriptionController
from app.core.dependencies import get_current_user
from app.models.ai_interaction import InteractionType
from app.models.user import User
from app.schemas.subscription import CreditCostOut, SubscriptionOut

router = APIRouter(prefix="/api/v1/subscription", tags=["Subscription"])


# =========================================================
# Get Subscription
# =========================================================

@router.get(
    "",
    response_model=SubscriptionOut | None,
    status_code=status.HTTP_200_OK,
)
def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionOut | None:
    """
    Returns the current user's subscription tier, status,
    billing period, and AI credit usage/remaining.
    """
    controller = SubscriptionController(db)
    return controller.get_subscription(current_user.id)


# =========================================================
# Get Credit Cost for an Interaction Type
# =========================================================

@router.get(
    "/credit-cost/{interaction_type}",
    response_model=CreditCostOut,
    status_code=status.HTTP_200_OK,
)
def get_credit_cost(
    interaction_type: InteractionType,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreditCostOut:
    """
    Returns how many credits a given AI interaction type costs
    — lets the frontend show the cost before the user commits
    to an action (e.g. "Generate Recipe (2 credits)").
    """
    controller = SubscriptionController(db)
    return controller.get_credit_cost(interaction_type)