"""
=========================================================
AIMeals Backend
Subscription Controller

Responsibilities:
    - Orchestrate read-only calls to SubscriptionService
    - Convert SQLAlchemy models into Pydantic response schemas

Dependencies:
    - app.services.subscription_service.SubscriptionService

Notes:
    - Deliberately read-only. SubscriptionService also has
      upgrade_tier() and reset_period(), but those aren't
      exposed via API yet — tier changes are billing-sensitive
      and no payment provider (Stripe / Google Play Billing /
      App Store) has been chosen yet. Exposing an upgrade
      endpoint before that decision would mean building
      against an assumption that might not hold. This can be
      added later without changing anything built here.
    - Controllers contain NO business logic. They orchestrate
      and translate only.
=========================================================
"""

import uuid

from sqlalchemy.orm import Session

from app.models.ai_interaction import InteractionType
from app.schemas.subscription import CreditCostOut, SubscriptionOut
from app.services.subscription_service import SubscriptionService


# =========================================================
# Subscription Controller
# =========================================================

class SubscriptionController:
    """
    Thin orchestration layer between API routes and SubscriptionService.
    """

    def __init__(self, db: Session):
        self.service = SubscriptionService(db)

    # ---------------------------------------------------
    # Get Subscription
    # ---------------------------------------------------

    def get_subscription(self, user_id: uuid.UUID) -> SubscriptionOut | None:
        """
        Returns None (not a 404) if the user somehow has no
        subscription — this should no longer be reachable in
        practice now that AuthService.register() provisions
        one automatically, but staying defensive here costs
        nothing and matches the Optional-check pattern used
        everywhere else in this project.
        """
        subscription = self.service.get_subscription(user_id)
        if subscription is None:
            return None

        return SubscriptionOut(
            id=subscription.id,
            tier=subscription.tier,
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            monthly_credit_allowance=subscription.monthly_credit_allowance,
            credits_used_this_period=subscription.credits_used_this_period,
            credits_remaining=(
                subscription.monthly_credit_allowance
                - subscription.credits_used_this_period
            ),
        )

    # ---------------------------------------------------
    # Get Credit Cost for an Interaction Type
    # ---------------------------------------------------

    def get_credit_cost(self, interaction_type: InteractionType) -> CreditCostOut:
        cost = self.service.get_credit_cost(interaction_type)
        return CreditCostOut(interaction_type=interaction_type, credit_cost=cost)