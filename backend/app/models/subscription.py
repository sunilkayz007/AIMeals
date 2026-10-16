"""
=========================================================
AIMeals Backend
Subscription Model

Responsibilities:
    - Define the subscriptions table schema
    - Define SubscriptionTier and SubscriptionStatus enums

Dependencies:
    - app.B_database.Base
    - app.models.user.User

Notes:
    - tier and status are DELIBERATELY separate fields.
      A user can be tier=PRO with status=CANCELLED — they
      cancelled, but should keep PRO access until
      current_period_end (standard billing UX pattern).
      Collapsing these into one field would make it
      impossible to represent that state correctly.
    - payment_provider / provider_subscription_id are
      generic and nullable: no payment processor has been
      chosen yet (Stripe vs Google Play Billing vs App
      Store). These fields store whichever provider's
      identifier is relevant once one is chosen, without
      assuming Stripe-specific fields prematurely.
    - One-to-one with User, same pattern as Profile.
    - monthly_credit_allowance / credits_used_this_period
      implement the tier-based AI cost control strategy:
      Free/Plus/Pro get different monthly credit budgets,
      and different interaction types (chat vs. meal plan
      generation) can cost different numbers of credits.
      credits_used_this_period resets to 0 when a new
      billing period starts (current_period_start/end).
    - bonus_credits_balance is a SEPARATE pool from
      monthly_credit_allowance, earned by watching AdMob
      rewarded ads (a flat REWARDED_AD_BONUS_CREDITS per
      ad watched, capped at the user's tier ceiling — see
      app/services/subscription_service.py's
      register_ad_watch()). Consumed as a FALLBACK only,
      after monthly_credit_allowance is exhausted — see
      SubscriptionService.check_and_consume_credit() and
      SubscriptionRepository.try_consume_with_bonus_fallback().
      UPDATE (Sep 2 2026): previously required watching TWO
      ads per grant (via a now-removed
      ads_watched_since_last_grant counter column) — simplified
      to a flat grant every single ad watch, since a fixed
      whole-number reward removed the need for batching.
    - ai_model_override lets a specific user be pinned to
      a particular Claude model regardless of their tier's
      default routing (e.g. for support/debug cases),
      without changing the tier-based routing logic itself.
      Null means "use the tier's default model."

Example usage:
    from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus

    sub = Subscription(
        user_id=user.id,
        tier=SubscriptionTier.FREE,
        status=SubscriptionStatus.ACTIVE,
    )
=========================================================
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Enums
# =========================================================

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PLUS = "plus"
    PRO = "pro"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# =========================================================
# Subscription Model
# =========================================================

class Subscription(Base):
    """
    Represents a user's subscription plan and billing state.

    Table: subscriptions
    One-to-one with User.
    """

    __tablename__ = "subscriptions"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Foreign Key (one-to-one)
    # ---------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------
    # Plan State
    # ---------------------------------------------------

    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier"),
        default=SubscriptionTier.FREE,
        nullable=False,
    )

    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )

    # ---------------------------------------------------
    # Billing Period
    # ---------------------------------------------------

    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ---------------------------------------------------
    # AI Credit Tracking
    # ---------------------------------------------------

    monthly_credit_allowance: Mapped[int] = mapped_column(
        Integer,
        default=20,
        nullable=False,
    )

    credits_used_this_period: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # ---------------------------------------------------
    # AdMob Rewarded-Ad Bonus Credits
    # ---------------------------------------------------
    # Separate pool from monthly_credit_allowance. Earned by
    # watching rewarded ads — a flat REWARDED_AD_BONUS_CREDITS
    # per ad watched, capped at the tier ceiling (see
    # app/services/subscription_service.py's register_ad_watch()).
    # Consumed as a FALLBACK only, after monthly_credit_allowance
    # is exhausted — see
    # SubscriptionService.check_and_consume_credit() and
    # SubscriptionRepository.try_consume_with_bonus_fallback().

    bonus_credits_balance: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    ai_model_override: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # ---------------------------------------------------
    # Payment Provider (generic, provider-agnostic)
    # ---------------------------------------------------

    payment_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    provider_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user = relationship("User")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user_id={self.user_id} tier={self.tier} status={self.status}>"