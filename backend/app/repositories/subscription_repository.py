"""
=========================================================
AIMeals Backend
Subscription Repository

Responsibilities:
    - Perform CRUD operations against the subscriptions table
    - Contains NO business logic beyond simple, mechanical
      credit-counter adjustments (these are data operations,
      not decisions — deciding WHETHER a user is allowed to
      spend a credit belongs in the service layer, not here)

Dependencies:
    - app.models.subscription.Subscription

Example usage:
    from app.repositories.subscription_repository import SubscriptionRepository

    repo = SubscriptionRepository(db)
    sub = repo.get_by_user_id(user.id)
    repo.increment_credits_used(sub)
=========================================================
"""

import uuid
from typing import Optional

from sqlalchemy import case, func, update
from sqlalchemy.orm import Session

from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier


# =========================================================
# Subscription Repository
# =========================================================

class SubscriptionRepository:
    """
    Encapsulates all direct database access for the Subscription model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Subscription]:
        return (
            self.db.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .first()
        )

    def get_by_id(self, subscription_id: uuid.UUID) -> Optional[Subscription]:
        return (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id)
            .first()
        )

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        monthly_credit_allowance: int = 20,
    ) -> Subscription:
        """
        Creates a new subscription for a user. Intended to be
        called once, typically right after registration, so
        every user has a Subscription row from day one.
        """
        new_subscription = Subscription(
            user_id=user_id,
            tier=tier,
            status=status,
            monthly_credit_allowance=monthly_credit_allowance,
        )

        self.db.add(new_subscription)
        self.db.commit()
        self.db.refresh(new_subscription)

        return new_subscription

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update(self, subscription: Subscription, **fields) -> Subscription:
        """
        Updates arbitrary fields — e.g. changing tier on upgrade,
        updating billing period dates from a payment webhook.
        """
        for key, value in fields.items():
            setattr(subscription, key, value)

        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    # ---------------------------------------------------
    # Credit Tracking Helpers
    # ---------------------------------------------------

    def increment_credits_used(
        self,
        subscription: Subscription,
        amount: int = 1,
    ) -> Subscription:
        """
        Increases credits_used_this_period by the given amount.

        This is a mechanical counter update only. Deciding
        whether the user is ALLOWED to spend this credit
        (i.e. checking against monthly_credit_allowance)
        is a business decision that belongs in the service
        layer, not here.

        NOTE: kept for callers that have already verified the
        allowance check themselves and just need the counter
        bumped unconditionally (e.g. a webhook-driven admin
        adjustment). For the actual credit-spending path, use
        try_increment_credits_used() below instead — this
        plain version is NOT safe against concurrent requests
        racing each other past the allowance limit.
        """
        subscription.credits_used_this_period += amount

        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def try_increment_credits_used(
        self,
        subscription_id: uuid.UUID,
        amount: int,
    ) -> bool:
        """
        Atomically increments credits_used_this_period ONLY IF
        doing so would not exceed monthly_credit_allowance —
        the check and the increment happen as a single
        indivisible database UPDATE, closing a real race
        condition where two simultaneous requests could each
        pass a Python-level check before either one commits
        (confirmed via code trace: two concurrent 1-credit
        requests at 1-credit-remaining could both succeed and
        both bill Claude, while the database only ever records
        one credit spent).

        Postgres row-level locking serializes concurrent UPDATE
        statements against the same row — the second request to
        actually execute sees the FIRST request's already-
        incremented value as part of its own WHERE clause
        evaluation, so if that would exceed the allowance, its
        UPDATE simply matches zero rows instead of racing past
        the check.

        Returns True if the increment succeeded (credit
        consumed), False if it didn't (would have exceeded the
        allowance — caller should treat this exactly like
        InsufficientCreditsError).
        """
        rows_matched = (
            self.db.query(Subscription)
            .filter(
                Subscription.id == subscription_id,
                Subscription.credits_used_this_period + amount
                <= Subscription.monthly_credit_allowance,
            )
            .update(
                {
                    Subscription.credits_used_this_period: Subscription.credits_used_this_period
                    + amount
                },
                synchronize_session=False,
            )
        )
        self.db.commit()
        return rows_matched > 0

    def try_consume_bonus_credits(
        self,
        subscription_id: uuid.UUID,
        amount: int,
    ) -> bool:
        """
        Atomically decrements bonus_credits_balance ONLY IF
        doing so would not take it below zero — same atomic
        "check and act in one UPDATE" pattern as
        try_increment_credits_used(), applied to the bonus
        pool instead of the monthly allowance. See that
        method's docstring for the full race-condition
        rationale; the mechanism here is identical.

        Returns True if the decrement succeeded (bonus credits
        consumed), False if the bonus balance was insufficient
        to cover amount.
        """
        rows_matched = (
            self.db.query(Subscription)
            .filter(
                Subscription.id == subscription_id,
                Subscription.bonus_credits_balance >= amount,
            )
            .update(
                {
                    Subscription.bonus_credits_balance: Subscription.bonus_credits_balance
                    - amount
                },
                synchronize_session=False,
            )
        )
        self.db.commit()
        return rows_matched > 0

    def try_consume_with_bonus_fallback(
        self,
        subscription_id: uuid.UUID,
        amount: int,
    ) -> bool:
        """
        The combined credit-spending gate: tries the monthly
        allowance first (via try_increment_credits_used()),
        and if that fails (allowance exhausted), falls back to
        the bonus_credits_balance pool earned from AdMob
        rewarded ads (via try_consume_bonus_credits()).

        Each of the two underlying attempts is independently
        atomic — there's no gap between "check" and "act"
        within either one, so trying them in sequence here
        does NOT reintroduce the race condition
        try_increment_credits_used() was built to close. If
        the monthly-allowance attempt fails, no state has
        changed yet, so the bonus attempt starts from a clean,
        current view of the row.

        Returns True if amount was successfully consumed from
        EITHER pool, False if neither pool could cover it (the
        caller should treat this exactly like
        InsufficientCreditsError, same as
        try_increment_credits_used() returning False).
        """
        if self.try_increment_credits_used(subscription_id, amount):
            return True
        return self.try_consume_bonus_credits(subscription_id, amount)

    def grant_bonus_credits(
        self,
        subscription_id: uuid.UUID,
        amount: int,
    ) -> Optional[Subscription]:
        """
        Adds to bonus_credits_balance. A pure increment, no
        allowance check needed since this only ever adds
        credits, never risks exceeding a ceiling on its own.

        NOTE: this method does NOT enforce any tier-cap ceiling
        — it's a raw, uncapped increment. For the actual
        ad-watch flow (which DOES need the tier cap), use
        register_ad_watch() below instead. This method is kept
        for any other caller that genuinely wants an
        unconditional grant (e.g. a manual admin/support
        credit).

        Returns the updated Subscription, or None if no
        subscription exists for this id.
        """
        subscription = (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id)
            .first()
        )
        if subscription is None:
            return None

        subscription.bonus_credits_balance += amount
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def register_ad_watch(
        self,
        subscription_id: uuid.UUID,
        grant_amount: int,
        tier_cap: int,
    ) -> tuple[Optional[Subscription], bool]:
        """
        Atomically grants credits for ONE rewarded-ad watch — a
        flat grant_amount, capped so bonus_credits_balance never
        exceeds tier_cap.

        UPDATE (Sep 2 2026): this used to implement a "2 ads = 5
        credits" mechanic via a since-removed
        ads_watched_since_last_grant counter column. Simplified
        to a flat per-ad grant — every single ad watch now
        grants credits immediately, no batching/counting needed.

        Done as ONE atomic UPDATE (via SQL GREATEST/LEAST,
        evaluated by Postgres itself), not a Python-level
        read-then-write — same race-condition rationale as
        try_increment_credits_used(): two rapid, near-
        simultaneous ad-watch callbacks for the same user must
        not both read a stale balance and both grant past the
        cap.

        grant_amount and tier_cap are passed in by the caller
        (the service layer) rather than looked up here — this
        repository stays free of tier/business logic, per its
        own docstring's rule; it only knows how to perform the
        mechanical, atomic balance update.

        Returns a tuple of (updated Subscription or None, did_grant):
            - (None, False) if no subscription exists for this id.
            - (subscription, True) if any credits were actually
              added (the common case).
            - (subscription, False) if the balance was already at
              or above tier_cap, so nothing more could be added
              (e.g. the user already has a full bonus balance).
        """
        actual_grant = func.greatest(
            0,
            func.least(grant_amount, tier_cap - Subscription.bonus_credits_balance),
        )

        stmt = (
            update(Subscription)
            .where(Subscription.id == subscription_id)
            .values(bonus_credits_balance=Subscription.bonus_credits_balance + actual_grant)
            .execution_options(synchronize_session="fetch")
            .returning(actual_grant)
        )

        result = self.db.execute(stmt)
        row = result.first()
        self.db.commit()

        if row is None:
            return None, False

        did_grant = row[0] > 0

        subscription = self.get_by_id(subscription_id)
        return subscription, did_grant

    def reset_credits_for_new_period(self, subscription: Subscription) -> Subscription:
        """
        Resets credits_used_this_period to 0. Called when a
        new billing period starts (e.g. monthly, or on
        renewal via a payment webhook).

        NOTE: bonus_credits_balance is deliberately NOT reset
        here — bonus credits earned from watching ads persist
        across billing periods and only decrease when actually
        spent (see try_consume_with_bonus_fallback()), unlike
        the monthly allowance which is meant to refresh each
        period.
        """
        subscription.credits_used_this_period = 0

        self.db.commit()
        self.db.refresh(subscription)

        return subscription