"""
=========================================================
AIMeals Backend
AdMob Rewarded-Ad Server-Side Verification (SSV) Callback

Endpoint:
    GET /api/v1/ads/ssv-callback   - called by Google's AdMob
                                      infrastructure after a
                                      user completes a rewarded
                                      ad view

⚠️  BEFORE GOING LIVE: this endpoint's signature verification
    (app.services.admob_verification.verify_ssv_signature) was
    written directly from Google's public SSV documentation but
    has NOT been exercised against Google's live infrastructure
    from this environment. Test it against Google's own SSV
    testing tool (AdMob console -> Mediation -> your rewarded ad
    unit -> SSV testing) before relying on it in production.

Expected AdMob SSV query parameters (per Google's SSV spec):
    ad_network      - numeric network id
    ad_unit         - ad unit id
    reward_amount   - reward amount configured in the AdMob UI
    reward_item     - reward item name configured in the AdMob UI
    timestamp       - epoch millis the reward was granted
    transaction_id  - unique id for this reward event; used here
                       for de-duplication (see
                       AdRewardTransactionRepository.record_if_new())
    user_id         - AdMob's "custom_data" field; this app sets
                       it to the AIMeals user's UUID when
                       requesting the rewarded ad client-side
    signature       - ECDSA signature over the query string
    key_id          - which of Google's published keys signed
                       this request

Processing order (each step can reject the callback):
    1. Verify the ECDSA signature against Google's published keys.
    2. Parse user_id as a UUID.
    3. Atomically record transaction_id — reject if already seen
       (replay/retry protection).
    4. Call SubscriptionService.register_ad_watch(), which grants
       a flat REWARDED_AD_BONUS_CREDITS per ad watch (Sep 2 2026:
       simplified from an earlier "2 ads = 5 credits" mechanic —
       every single ad watch now grants credits immediately),
       capped at the user's tier ceiling.

Dependencies:
    - app.services.admob_verification.verify_ssv_signature
    - app.services.subscription_service.SubscriptionService
    - app.repositories.ad_reward_transaction_repository.AdRewardTransactionRepository
    - app.B_database.get_db
=========================================================
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.repositories.ad_reward_transaction_repository import (
    AdRewardTransactionRepository,
)
from app.services.admob_verification import verify_ssv_signature
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/v1/ads", tags=["Ads"])


@router.get("/ssv-callback")
async def ssv_callback(
    request: Request,
    ad_network: str = Query(...),
    ad_unit: str = Query(...),
    reward_amount: str = Query(...),
    reward_item: str = Query(...),
    timestamp: str = Query(...),
    transaction_id: str = Query(...),
    user_id: str = Query(..., description="AIMeals user UUID, passed through as AdMob's custom_data"),
    signature: str = Query(...),
    key_id: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """
    Called by Google's AdMob servers after a user finishes
    watching a rewarded ad. NOT called by the AIMeals app or
    client directly — there is no Authorization header here,
    since this is a server-to-server callback from Google, not
    an authenticated AIMeals API request. Trust comes entirely
    from verify_ssv_signature() below.

    request.url.query (the RAW query string, not the parsed
    Query(...) params above) is what's passed to
    verify_ssv_signature() — parameter order in the original
    string matters for reconstructing the exact content Google
    signed, and re-serializing the parsed params could reorder
    or re-encode them differently.
    """
    is_valid = await verify_ssv_signature(
        raw_query_string=request.url.query,
        signature=signature,
        key_id=key_id,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSV signature verification failed.",
        )

    try:
        parsed_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id was not a valid UUID.",
        )

    transaction_repo = AdRewardTransactionRepository(db)
    is_new_transaction = transaction_repo.record_if_new(
        transaction_id=transaction_id,
        user_id=parsed_user_id,
    )

    if not is_new_transaction:
        # Already processed this exact reward event — do not grant
        # credits again. Not an error from Google's point of view
        # (retries are expected/normal), so respond 200.
        return {
            "granted": False,
            "duplicate": True,
        }

    service = SubscriptionService(db)
    subscription, did_grant = service.register_ad_watch(parsed_user_id)

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found for this user_id.",
        )

    return {
        "granted": did_grant,
        "duplicate": False,
        "bonus_credits_balance": subscription.bonus_credits_balance,
    }