"""
=========================================================
AIMeals Backend
Subscription Service

Responsibilities:
    - Decide which Claude model a user's tier should use
    - Enforce AI credit limits before an AI call is allowed
    - Own the credit-cost-per-interaction-type lookup table
    - Handle tier upgrades/downgrades and period resets
    - Grant a one-time "grace" chat message after credits run
      out, so the chat feature degrades gracefully into an
      upsell rather than a hard error on the message that
      first discovers the user is out of credits
    - Grant AdMob rewarded-ad bonus credits
    - Apply RevenueCat webhook events to a user's subscription

Dependencies:
    - app.repositories.subscription_repository.SubscriptionRepository
    - app.core.exceptions.InsufficientCreditsError

Notes:
    - check_and_consume_credit() is the single decision point
      every future AI-calling service (recipe generation,
      chat, image analysis, etc.) must call BEFORE actually
      hitting the Claude API. This is what makes the credit
      system real rather than theoretical — the enforcement
      happens here, once, rather than being re-implemented
      (and potentially forgotten) in every service that
      calls Claude.
    - Credit costs are intentionally NOT proportional to
      exact token cost — they're rounded to whole numbers
      that roughly reflect relative expense, so the credit
      system stays simple to reason about for users ("this
      costs 5 credits") rather than exposing token-level
      precision.
    - As of the AdMob rewarded-ads feature,
      check_and_consume_credit() draws from TWO pools in
      order: monthly_credit_allowance first, then
      bonus_credits_balance (earned by watching rewarded
      ads) as a fallback once the monthly allowance is
      exhausted. See
      SubscriptionRepository.try_consume_with_bonus_fallback()
      for the atomic mechanics. Every caller of
      check_and_consume_credit() gets this fallback
      automatically — no caller-side changes needed.
    - has_used_chat_grace()/consume_chat_grace()/rollback_chat_grace()
      are a DELIBERATE, NARROW exception to the hard ceiling
      check_and_consume_credit() enforces — used only by
      AIService.send_chat_message_stream(), for chat
      specifically. Every other AI feature remains hard-capped
      exactly as before. See that method for the calling logic.
    - is_paid_tier() is a NEW helper added for the allergen
      deep-insight feature (Sonnet, Plus/Pro only) — the first
      feature in the app that's tier-gated outright rather
      than just credit-metered. A Free-tier user is blocked
      from calling the deep-insight endpoint at all, even if
      check_and_consume_credit() would otherwise let them
      afford it (Free tier does have some credit allowance).
      Called by AIService.get_allergen_deep_insight() BEFORE
      check_and_consume_credit(), so a Free user gets a clear
      "upgrade required" response rather than a generic
      credits error.
    - register_ad_watch() grants REWARDED_AD_BONUS_CREDITS (a
      flat amount) every single rewarded-ad watch, capped at
      the user's tier ceiling. This is the correct entry point
      for the AdMob SSV callback flow — see app/api/v1/ads.py.
      grant_bonus_credits() (below) still exists for any caller
      that wants an uncapped, unconditional grant (e.g. a
      manual admin/support credit), but the ad-watch flow
      itself should call register_ad_watch(), not
      grant_bonus_credits(), directly.
      UPDATE (Sep 2 2026): previously implemented a "2 ads = 5
      credits" mechanic (finalized Aug 30 2026) requiring two
      ad watches per grant, tracked via a since-removed
      ads_watched_since_last_grant counter column. Simplified
      to a flat per-ad grant — simpler for users to understand
      ("watch an ad, get credits, every time") and simpler to
      implement.
    - apply_revenuecat_event() is the entry point for the
      RevenueCat webhook (see app/api/v1/revenuecat_webhook.py).
      PRODUCT_ID_TO_TIER below maps RevenueCat/store product ids
      to a SubscriptionTier — update it once real product ids
      are finalized in RevenueCat/Play Console (currently
      placeholders). See apply_revenuecat_event()'s own
      docstring for the per-event-type behavior.

Example usage:
    from app.services.subscription_service import SubscriptionService
    from app.models.ai_interaction import InteractionType

    service = SubscriptionService(db)
    model = service.get_model_for_user(user.id)
    service.check_and_consume_credit(user.id, InteractionType.CHAT)
    # ... now safe to actually call the Claude API ...
=========================================================
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import InsufficientCreditsError
from app.models.ai_interaction import InteractionType
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier
from app.repositories.subscription_repository import SubscriptionRepository


# =========================================================
# Credit Cost Lookup
# =========================================================

# Relative cost per interaction type, in credits. Roughly
# reflects actual API cost tiers from the cost strategy
# analysis: cheap calls (chat) cost 1, expensive calls
# (meal plan generation) cost proportionally more.
INTERACTION_CREDIT_COSTS: dict[InteractionType, int] = {
    InteractionType.CHAT: 1,
    InteractionType.RECIPE_GENERATION: 2,
    InteractionType.FOOD_IMAGE_ANALYSIS: 4,
    InteractionType.PANTRY_SUGGESTION: 2,
    InteractionType.MEAL_PLAN_GENERATION: 5,
    InteractionType.INGREDIENT_IMAGE_IDENTIFY: 2,
    InteractionType.INGREDIENT_PHOTO_RECIPE: 2,
    # Sonnet, Plus/Pro-only (see is_paid_tier() below) — charged
    # once per user per allergen, on first unlock only. Priced
    # like RECIPE_GENERATION/PANTRY_SUGGESTION, the app's other
    # "one clear artifact produced" Sonnet-tier calls.
    InteractionType.ALLERGEN_DEEP_INSIGHT: 2,
    # Health Insights feature ("From Report to Plate") — a
    # single vision/document-heavy extraction call, same shape
    # and cost tier as FOOD_IMAGE_ANALYSIS.
    InteractionType.HEALTH_REPORT_ANALYSIS: 4,
    # "Estimate with AI" on the manual meal-log form — a single,
    # cheap text-only call. Priced like CHAT, the app's other
    # simple single-turn text interaction.
    InteractionType.ESTIMATE_MEAL_NUTRITION: 1,
}


# =========================================================
# Tier -> Model Routing
# =========================================================

TIER_DEFAULT_MODELS: dict[SubscriptionTier, str] = {
    SubscriptionTier.FREE: "claude-haiku-4-5",
    SubscriptionTier.PLUS: "claude-sonnet-5",
    SubscriptionTier.PRO: "claude-sonnet-5",  # Opus used selectively per-call, not as the tier default
}

# Default credit allowances applied on tier change/creation.
TIER_DEFAULT_ALLOWANCES: dict[SubscriptionTier, int] = {
    SubscriptionTier.FREE: 50,
    SubscriptionTier.PLUS: 300,
    SubscriptionTier.PRO: 600,
}

# AdMob rewarded-ad bonus credit amount, granted every SINGLE
# completed ad watch (see register_ad_watch()), capped at the
# user's tier ceiling. Simplified Sep 2 2026 from an earlier
# "2 ads = 5 credits" batching mechanic to this flat per-ad
# grant. No daily cap on number of ad watches.
REWARDED_AD_BONUS_CREDITS: int = 3


# =========================================================
# RevenueCat Product -> Tier Mapping
# =========================================================

# Maps RevenueCat/store product ids to the SubscriptionTier they
# grant. ⚠️ PLACEHOLDER IDS — swap these for the real product ids
# once finalized in the RevenueCat dashboard / Google Play
# Console. Both monthly and annual products for a tier map to the
# SAME SubscriptionTier; billing period itself isn't tracked as a
# separate field on Subscription (current_period_start/end already
# capture the actual dates from RevenueCat regardless of period
# length), so no monthly/annual distinction is needed here beyond
# which tier a purchase unlocks.
PRODUCT_ID_TO_TIER: dict[str, SubscriptionTier] = {
    "aimeals_plus_monthly": SubscriptionTier.PLUS,
    "aimeals_plus_annual": SubscriptionTier.PLUS,
    "aimeals_pro_monthly": SubscriptionTier.PRO,
    "aimeals_pro_annual": SubscriptionTier.PRO,
}

# RevenueCat event types that grant/renew access at the mapped
# tier, with a FRESH billing period (credits_used_this_period
# reset to 0). A brand-new purchase and a normal renewal are
# handled identically — both mean "a new period just started at
# this tier."
_GRANTING_EVENT_TYPES = {"INITIAL_PURCHASE", "RENEWAL", "UNCANCELLATION"}

# A user changed products (upgrade/downgrade) mid-cycle. Tier and
# allowance change immediately, but credits_used_this_period is
# NOT reset — same semantics as the existing upgrade_tier() method,
# since this isn't a new billing period, just a new ceiling.
_PRODUCT_CHANGE_EVENT_TYPES = {"PRODUCT_CHANGE"}

# The subscription was cancelled but the user keeps access until
# current_period_end (RevenueCat/the store already enforce this on
# their end — this just records it for the UI, e.g. "Cancels on
# <date>" messaging). Tier is NOT downgraded here.
_CANCELLING_EVENT_TYPES = {"CANCELLATION"}

# Access has actually ended — downgrade to Free now.
_EXPIRING_EVENT_TYPES = {"EXPIRATION"}


def _ms_to_datetime(epoch_ms: Optional[int]) -> Optional[datetime]:
    """
    Converts a RevenueCat epoch-milliseconds timestamp to a
    timezone-aware UTC datetime. Returns None if epoch_ms is None
    (RevenueCat doesn't always populate every timestamp field for
    every event type).
    """
    if epoch_ms is None:
        return None
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)


# =========================================================
# Subscription Service
# =========================================================

class SubscriptionService:
    """
    Contains the business logic for subscription management
    and AI credit enforcement.
    """

    def __init__(self, db: Session):
        self.db = db
        self.subscription_repo = SubscriptionRepository(db)

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_subscription(self, user_id: uuid.UUID) -> Optional[Subscription]:
        return self.subscription_repo.get_by_user_id(user_id)

    def create_default_subscription(
        self, user_id: uuid.UUID, credit_allowance_override: Optional[int] = None
    ) -> Subscription:
        """
        Creates a Free-tier subscription. Intended to be
        called once, right after user registration.

        credit_allowance_override, if given, replaces the
        normal default (TIER_DEFAULT_ALLOWANCES[FREE]) — used
        by AuthService to grant 0 credits when an email has
        already claimed a free tier before (detected via
        UsedEmail, which survives account deletion). Everything
        else about the subscription (tier, status) is
        unaffected — a returning email still gets a normal,
        fully-functional Free-tier account, just without a
        fresh batch of AI credits to farm.
        """
        allowance = (
            credit_allowance_override
            if credit_allowance_override is not None
            else TIER_DEFAULT_ALLOWANCES[SubscriptionTier.FREE]
        )
        return self.subscription_repo.create(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            monthly_credit_allowance=allowance,
        )

    # ---------------------------------------------------
    # Model Routing
    # ---------------------------------------------------

    def get_model_for_user(self, user_id: uuid.UUID) -> str:
        """
        Returns which Claude model should be used for this
        user's AI calls. Checks ai_model_override first (lets
        a specific user be pinned to a model regardless of
        tier, e.g. for support/debug cases); falls back to
        the tier's default model otherwise.

        If the user has no subscription at all (shouldn't
        normally happen if create_default_subscription is
        called at registration, but handled defensively),
        falls back to the Free tier's model as the safest
        default.
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)

        if subscription is None:
            return TIER_DEFAULT_MODELS[SubscriptionTier.FREE]

        if subscription.ai_model_override:
            return subscription.ai_model_override

        return TIER_DEFAULT_MODELS[subscription.tier]

    def get_tier_for_user(self, user_id: uuid.UUID) -> SubscriptionTier:
        """
        Returns this user's actual subscription tier -- unlike
        get_model_for_user(), this deliberately ignores
        ai_model_override, since that's a support/debug knob for
        which MODEL a call uses, not a statement about what plan
        the user is actually on. Used where a feature needs to
        vary by PLAN specifically (e.g. Coach chat's per-tier
        response depth -- see ai_service.py's
        _NUTRITION_COACH_DEPTH_* prompts).

        Same defensive Free-tier fallback as get_model_for_user()
        for a user with no subscription row at all.
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)

        if subscription is None:
            return SubscriptionTier.FREE

        return subscription.tier

    # ---------------------------------------------------
    # Tier Gating (hard block, independent of credit balance)
    # ---------------------------------------------------

    def is_paid_tier(self, user_id: uuid.UUID) -> bool:
        """
        True if the user is on Plus or Pro. Used for features
        that should be entirely unavailable on Free regardless
        of credit balance (currently just the allergen
        deep-insight feature) — distinct from the normal
        credit-metering every other feature uses, where Free
        users CAN use the feature as long as they have credits.

        False (not an error) if the user has no subscription
        at all — treated the same as Free.
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)
        if subscription is None:
            return False
        return subscription.tier in (SubscriptionTier.PLUS, SubscriptionTier.PRO)

    # ---------------------------------------------------
    # Credit Enforcement (core method)
    # ---------------------------------------------------

    def get_credit_cost(self, interaction_type: InteractionType) -> int:
        """
        Returns the credit cost for a given interaction type.

        Raises a clear, actionable error (not a bare KeyError)
        if interaction_type is missing from
        INTERACTION_CREDIT_COSTS — this has happened for real
        once already (a new InteractionType value was added to
        the enum without a matching entry here, silently
        breaking every route that used it until a live test
        surfaced a cryptic KeyError). Every InteractionType
        member MUST have an entry in that dict.
        """
        if interaction_type not in INTERACTION_CREDIT_COSTS:
            raise ValueError(
                f"No credit cost defined for interaction_type={interaction_type!r}. "
                f"Add it to INTERACTION_CREDIT_COSTS in subscription_service.py — "
                f"every InteractionType enum member must have an entry there."
            )
        return INTERACTION_CREDIT_COSTS[interaction_type]

    def get_available_credits(self, user_id: uuid.UUID) -> int:
        """
        Returns how many credits the user currently has left
        this period, WITHOUT consuming anything — a pure read,
        for callers that need to check affordability of a
        multi-step operation up front (e.g. meal plan chunk
        generation, where the total cost across several chunks
        needs to be checked BEFORE any of them run) rather than
        discovering InsufficientCreditsError partway through.

        Includes bonus_credits_balance in the total, matching
        check_and_consume_credit()'s two-pool fallback — a
        caller checking affordability should see the same
        total that would actually be usable.

        Returns 0 if the user has no subscription at all,
        matching check_and_consume_credit()'s treatment of
        that case as "cannot afford anything."
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)
        if subscription is None:
            return 0
        monthly_remaining = max(
            0, subscription.monthly_credit_allowance - subscription.credits_used_this_period
        )
        return monthly_remaining + subscription.bonus_credits_balance

    def check_and_consume_credit(
        self,
        user_id: uuid.UUID,
        interaction_type: InteractionType,
    ) -> Subscription:
        """
        The core enforcement gate. Must be called BEFORE
        actually making an AI API call.

        Checks whether the user has enough remaining credits
        for this interaction type, and consumes them, as ONE
        atomic database operation — see
        SubscriptionRepository.try_increment_credits_used()'s
        docstring for why this matters: a plain Python-level
        check-then-write here was a confirmed real race
        condition (two simultaneous requests at 1-credit-
        remaining could both pass the check and both bill
        Claude, while the database only ever recorded one
        credit spent).

        Draws from monthly_credit_allowance first, falling
        back to bonus_credits_balance (AdMob rewarded-ad
        credits) if the monthly allowance is exhausted — see
        SubscriptionRepository.try_consume_with_bonus_fallback().
        This fallback is automatic; no caller-side change is
        needed to benefit from it.

        Raises:
            InsufficientCreditsError: if the user has no
                subscription, or consuming this credit cost
                would exceed BOTH their monthly_credit_allowance
                AND their bonus_credits_balance.
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)

        if subscription is None:
            raise InsufficientCreditsError(
                "User has no subscription; cannot verify credit allowance."
            )

        cost = self.get_credit_cost(interaction_type)

        success = self.subscription_repo.try_consume_with_bonus_fallback(
            subscription.id, cost
        )

        if not success:
            self.db.refresh(subscription)
            remaining = (
                subscription.monthly_credit_allowance
                - subscription.credits_used_this_period
                + subscription.bonus_credits_balance
            )
            raise InsufficientCreditsError(
                f"This action costs {cost} credits, but only "
                f"{max(0, remaining)} remain (including bonus credits)."
            )

        self.db.refresh(subscription)
        return subscription

    def refund_credit(
        self,
        user_id: uuid.UUID,
        interaction_type: InteractionType,
    ) -> Optional[Subscription]:
        """
        Refunds the credit cost for a given interaction type,
        for use when a Claude API call fails AFTER credits
        were already consumed by check_and_consume_credit().
        This keeps the credit system fair — a failed call
        that delivered nothing shouldn't cost the user.

        NOTE: refunds always go back to
        credits_used_this_period (the monthly pool), even if
        the original consumption actually drew from
        bonus_credits_balance. This is a deliberate
        simplification — check_and_consume_credit() does not
        currently report back WHICH pool a given consumption
        drew from, so refund_credit() cannot distinguish
        either. In the rare case a bonus-funded call fails,
        this refunds the user's monthly allowance instead of
        their bonus balance — still a full, fair refund of the
        credit cost either way, just credited to the other
        pool. Revisit if bonus-vs-monthly refund precision
        becomes worth the added complexity.

        Clamped at 0: credits_used_this_period will never go
        negative, even if called incorrectly or more than once.

        Returns None if the user has no subscription (should
        not normally happen if check_and_consume_credit()
        already succeeded for this user, but handled
        defensively).
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)

        if subscription is None:
            return None

        cost = self.get_credit_cost(interaction_type)
        refunded_amount = min(cost, subscription.credits_used_this_period)

        return self.subscription_repo.increment_credits_used(
            subscription, amount=-refunded_amount
        )

    # ---------------------------------------------------
    # AdMob Rewarded-Ad Bonus Credits
    # ---------------------------------------------------

    def grant_bonus_credits(
        self,
        user_id: uuid.UUID,
        amount: int = REWARDED_AD_BONUS_CREDITS,
    ) -> Optional[Subscription]:
        """
        Grants bonus credits to a user's bonus_credits_balance,
        unconditionally and without a tier-cap check. Kept for
        any caller that genuinely wants a raw, uncapped grant
        (e.g. a manual admin/support credit).

        The actual AdMob rewarded-ad SSV callback flow should
        call register_ad_watch() instead — that method
        implements the real per-ad grant with the tier-cap
        ceiling. This method does NOT enforce any cap, so using
        it directly for ad-watch grants would bypass the
        ceiling entirely.

        amount defaults to REWARDED_AD_BONUS_CREDITS (3).

        Returns the updated Subscription, or None if the user
        has no subscription.
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)
        if subscription is None:
            return None
        return self.subscription_repo.grant_bonus_credits(subscription.id, amount)

    def register_ad_watch(
        self, user_id: uuid.UUID
    ) -> tuple[Optional[Subscription], bool]:
        """
        Registers ONE rewarded-ad watch, granting
        REWARDED_AD_BONUS_CREDITS (currently 3) immediately,
        capped at the user's tier ceiling. This is the correct
        entry point for the AdMob SSV callback handler (see
        app/api/v1/ads.py) — do not call grant_bonus_credits()
        directly from that flow, since it has no tier cap.

        UPDATE (Sep 2 2026): every single ad watch now grants
        credits immediately — no batching. (Previously required
        two ad watches per grant; simplified for clarity.)

        Resolves the user's tier cap (TIER_DEFAULT_ALLOWANCES
        for their current tier) and delegates the atomic grant
        logic to SubscriptionRepository.register_ad_watch() —
        see that method's docstring for the exact mechanics
        (one atomic UPDATE, capped via SQL GREATEST/LEAST).

        Returns a tuple of (updated Subscription or None, did_grant):
            - (None, False) if the user has no subscription.
            - (subscription, True) if credits were actually
              added (the common case).
            - (subscription, False) if the bonus balance was
              already at the tier cap, so nothing more could be
              added.
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)
        if subscription is None:
            return None, False

        tier_cap = TIER_DEFAULT_ALLOWANCES[subscription.tier]

        return self.subscription_repo.register_ad_watch(
            subscription.id,
            grant_amount=REWARDED_AD_BONUS_CREDITS,
            tier_cap=tier_cap,
        )

    # ---------------------------------------------------
    # Chat Grace (one-time courtesy message after credits run out)
    # ---------------------------------------------------

    def has_used_chat_grace(self, user_id: uuid.UUID) -> bool:
        """
        True if the user has already used their one free
        "grace" chat message this period after running out of
        credits. Detected as credits_used_this_period exceeding
        the normal monthly_credit_allowance ceiling — the grace
        message is the ONLY thing allowed to push usage past
        that ceiling. Everything else in this service (chat's
        own normal check_and_consume_credit() calls, every
        other AI feature) is still hard-capped at the ceiling
        exactly as before; this is a deliberate, narrow
        exception used only by AIService.send_chat_message_stream().
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)
        if subscription is None:
            return True  # no subscription at all -> no grace to give
        return subscription.credits_used_this_period > subscription.monthly_credit_allowance

    def consume_chat_grace(self, user_id: uuid.UUID) -> None:
        """
        Marks the one-time chat grace message as used by
        pushing credits_used_this_period one CHAT-cost over the
        normal allowance.
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)
        if subscription is not None:
            cost = self.get_credit_cost(InteractionType.CHAT)
            self.subscription_repo.increment_credits_used(subscription, amount=cost)

    def rollback_chat_grace(self, user_id: uuid.UUID) -> None:
        """
        Undoes consume_chat_grace() — used if the Claude call
        fails AFTER the grace was marked used, so a network/API
        failure doesn't burn the user's one free grace message
        without them actually getting a reply.
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)
        if subscription is not None:
            cost = self.get_credit_cost(InteractionType.CHAT)
            self.subscription_repo.increment_credits_used(subscription, amount=-cost)

    # ---------------------------------------------------
    # Tier Management
    # ---------------------------------------------------

    def upgrade_tier(self, user_id: uuid.UUID, new_tier: SubscriptionTier) -> Subscription:
        """
        Changes a user's tier and updates their credit
        allowance to match the new tier's default. Does NOT
        reset credits_used_this_period — an upgrade mid-period
        should increase the ceiling, not grant a fresh period.

        Raises:
            ValueError: if the user has no subscription to
                upgrade. This is a programming error (the
                caller should have created a subscription at
                registration), surfaced clearly rather than
                as an implicit AttributeError.
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)

        if subscription is None:
            raise ValueError(
                f"Cannot upgrade tier: user {user_id} has no subscription."
            )

        return self.subscription_repo.update(
            subscription,
            tier=new_tier,
            monthly_credit_allowance=TIER_DEFAULT_ALLOWANCES[new_tier],
        )

    def reset_period(self, user_id: uuid.UUID) -> Optional[Subscription]:
        """
        Resets credits_used_this_period to 0. Intended to be
        called when a new billing period starts (e.g. via a
        scheduled job or a payment provider's renewal webhook,
        once one is chosen).

        bonus_credits_balance is deliberately untouched — see
        SubscriptionRepository.reset_credits_for_new_period().
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)

        if subscription is None:
            return None

        return self.subscription_repo.reset_credits_for_new_period(subscription)

    # ---------------------------------------------------
    # RevenueCat Webhook Application
    # ---------------------------------------------------

    def apply_revenuecat_event(
        self,
        user_id: uuid.UUID,
        event_type: str,
        product_id: Optional[str],
        purchased_at_ms: Optional[int],
        expiration_at_ms: Optional[int],
        provider_subscription_id: Optional[str],
    ) -> Optional[Subscription]:
        """
        Applies a single RevenueCat webhook event to a user's
        subscription. Called by app/api/v1/revenuecat_webhook.py
        AFTER the event has already been verified (bearer token)
        and de-duplicated (RevenueCatWebhookEventRepository) —
        this method assumes it's being called exactly once per
        real event and does not itself check for duplicates.

        Behavior by event_type:
            INITIAL_PURCHASE / RENEWAL / UNCANCELLATION:
                A fresh billing period just started at the tier
                mapped from product_id. Sets tier, status=ACTIVE,
                monthly_credit_allowance to that tier's default,
                current_period_start/end from the event's
                timestamps, cancel_at_period_end=False, and
                RESETS credits_used_this_period to 0 (new period,
                new allowance).
            PRODUCT_CHANGE:
                User upgraded/downgraded mid-cycle. Sets tier and
                monthly_credit_allowance to the new tier's
                default, updates current_period_end if provided,
                but does NOT reset credits_used_this_period —
                same semantics as the existing upgrade_tier().
            CANCELLATION:
                User cancelled but keeps access until the period
                ends (RevenueCat/the store enforce this on their
                end regardless). Sets status=CANCELLED,
                cancel_at_period_end=True. Tier is UNCHANGED.
            EXPIRATION:
                Access has actually ended. Downgrades to Free
                tier, status=EXPIRED, resets
                monthly_credit_allowance to the Free default.
                Does NOT touch credits_used_this_period (no
                reason to — Free's own reset_period()/next
                period will handle that normally).
            Anything else (e.g. BILLING_ISSUE, TRANSFER,
            SUBSCRIPTION_PAUSED, TEST): no-op. RevenueCat/the
            store continue enforcing access on their end during a
            billing-issue grace period; this app only needs to
            react once an EXPIRATION actually arrives.

        product_id is required (and must be a KEY in
        PRODUCT_ID_TO_TIER) for every event type EXCEPT
        CANCELLATION and EXPIRATION, which don't need to look up
        a tier to downgrade/mark cancelled.

        Returns the updated Subscription, or None if:
            - the user has no subscription at all, or
            - event_type requires a tier lookup and product_id
              is missing or unrecognized (logged as a ValueError
              by the caller — see the route's error handling).
        """
        subscription = self.subscription_repo.get_by_user_id(user_id)
        if subscription is None:
            return None

        if event_type in _GRANTING_EVENT_TYPES:
            tier = PRODUCT_ID_TO_TIER.get(product_id or "")
            if tier is None:
                raise ValueError(
                    f"Unrecognized or missing product_id={product_id!r} for "
                    f"event_type={event_type!r}. Add it to PRODUCT_ID_TO_TIER "
                    f"in subscription_service.py."
                )
            return self.subscription_repo.update(
                subscription,
                tier=tier,
                status=SubscriptionStatus.ACTIVE,
                monthly_credit_allowance=TIER_DEFAULT_ALLOWANCES[tier],
                credits_used_this_period=0,
                current_period_start=_ms_to_datetime(purchased_at_ms),
                current_period_end=_ms_to_datetime(expiration_at_ms),
                cancel_at_period_end=False,
                payment_provider="revenuecat",
                provider_subscription_id=provider_subscription_id,
            )

        if event_type in _PRODUCT_CHANGE_EVENT_TYPES:
            tier = PRODUCT_ID_TO_TIER.get(product_id or "")
            if tier is None:
                raise ValueError(
                    f"Unrecognized or missing product_id={product_id!r} for "
                    f"event_type={event_type!r}. Add it to PRODUCT_ID_TO_TIER "
                    f"in subscription_service.py."
                )
            return self.subscription_repo.update(
                subscription,
                tier=tier,
                monthly_credit_allowance=TIER_DEFAULT_ALLOWANCES[tier],
                current_period_end=_ms_to_datetime(expiration_at_ms)
                or subscription.current_period_end,
                payment_provider="revenuecat",
                provider_subscription_id=provider_subscription_id,
            )

        if event_type in _CANCELLING_EVENT_TYPES:
            return self.subscription_repo.update(
                subscription,
                status=SubscriptionStatus.CANCELLED,
                cancel_at_period_end=True,
            )

        if event_type in _EXPIRING_EVENT_TYPES:
            return self.subscription_repo.update(
                subscription,
                tier=SubscriptionTier.FREE,
                status=SubscriptionStatus.EXPIRED,
                monthly_credit_allowance=TIER_DEFAULT_ALLOWANCES[SubscriptionTier.FREE],
                cancel_at_period_end=False,
            )

        # Unhandled event type (BILLING_ISSUE, TRANSFER,
        # SUBSCRIPTION_PAUSED, TEST, etc.) — deliberately a no-op.
        return subscription
