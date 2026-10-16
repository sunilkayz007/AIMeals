"""
=========================================================
AIMeals Backend
Subscription Schemas

Responsibilities:
    - Define response shapes for subscription/credit data

Dependencies:
    - app.models.subscription (SubscriptionTier, SubscriptionStatus)
    - app.models.ai_interaction.InteractionType

Notes:
    - Read-only for now, by design (see subscription_controller.py
      docstring): tier changes and billing are deliberately not
      exposed yet, since no payment provider has been chosen.

Example usage:
    from app.schemas.subscription import SubscriptionOut

    def get_subscription() -> SubscriptionOut:
        ...
=========================================================
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.ai_interaction import InteractionType
from app.models.subscription import SubscriptionStatus, SubscriptionTier


# =========================================================
# Response Schema — Subscription
# =========================================================

class SubscriptionOut(BaseModel):
    """
    Shape of subscription data returned to the client.

    credits_remaining is computed (monthly_credit_allowance -
    credits_used_this_period), not a stored column — built
    manually in the controller, not via model_validate.
    """

    id: uuid.UUID
    tier: SubscriptionTier
    status: SubscriptionStatus
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    monthly_credit_allowance: int
    credits_used_this_period: int
    credits_remaining: int


# =========================================================
# Response Schema — Credit Cost Lookup
# =========================================================

class CreditCostOut(BaseModel):
    """
    Shape returned by GET /subscription/credit-cost/{interaction_type}.

    Lets the frontend show "this will cost N credits" before
    the user commits to an AI action, without hardcoding the
    cost table client-side.
    """

    interaction_type: InteractionType
    credit_cost: int