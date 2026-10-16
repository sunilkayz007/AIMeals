"""
=========================================================
AIMeals Backend
RevenueCat Webhook Endpoint

Endpoint:
    POST /api/v1/billing/revenuecat-webhook   - called by
        RevenueCat's servers on every subscription lifecycle
        event (purchase, renewal, cancellation, expiration, etc.)

Requires "Authorization: Bearer <REVENUECAT_WEBHOOK_SECRET>" —
the SAME secret must be set in both this app's .env and in the
RevenueCat dashboard (Project Settings -> Integrations ->
Webhooks -> Authorization header value). This is RevenueCat's
only authentication mechanism for webhooks — there's no request
signature to verify (unlike AdMob's SSV), so this header IS the
entire trust boundary. If REVENUECAT_WEBHOOK_SECRET is left blank
in settings, every request is rejected (fail closed).

Processing order (each step can reject/skip the event):
    1. Verify the Authorization bearer token against settings.
    2. Parse app_user_id as a UUID (this app sets RevenueCat's
       app_user_id to the AIMeals user's own UUID client-side at
       SDK init time).
    3. Atomically record event.id — skip (200, no-op) if already
       processed (RevenueCat retries on non-2xx, and can
       occasionally redeliver even successfully-processed
       events).
    4. Apply the event via SubscriptionService.apply_revenuecat_event().

Notes:
    - Always returns 2xx once the event is authenticated and
      parseable, even for a "no matching subscription" or
      "unhandled event type" case — RevenueCat treats any
      non-2xx response as delivery failure and will retry
      repeatedly. Only auth failures and malformed payloads
      should ever produce a non-2xx from this endpoint.

Dependencies:
    - app.schemas.revenuecat_webhook.RevenueCatWebhookPayload
    - app.services.subscription_service.SubscriptionService
    - app.repositories.revenuecat_webhook_event_repository.RevenueCatWebhookEventRepository
    - app.B_database.get_db
=========================================================
"""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.A_config import settings
from app.B_database import get_db
from app.C_logger import app_logger
from app.repositories.revenuecat_webhook_event_repository import (
    RevenueCatWebhookEventRepository,
)
from app.schemas.revenuecat_webhook import RevenueCatWebhookPayload
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])


def _verify_bearer_token(authorization: str | None) -> None:
    """
    Raises HTTPException(401) unless authorization is exactly
    "Bearer <REVENUECAT_WEBHOOK_SECRET>". Fails closed: if the
    secret isn't configured (empty string), every request is
    rejected rather than silently accepted.
    """
    expected = settings.REVENUECAT_WEBHOOK_SECRET
    if not expected:
        app_logger.error(
            "REVENUECAT_WEBHOOK_SECRET is not configured — rejecting "
            "all RevenueCat webhook requests until it is set."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook not configured.",
        )

    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header.",
        )


@router.post("/revenuecat-webhook")
async def revenuecat_webhook(
    payload: RevenueCatWebhookPayload,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """
    RevenueCat webhook receiver. See module docstring for the
    full processing order and trust model.
    """
    _verify_bearer_token(authorization)

    event = payload.event

    try:
        user_id = uuid.UUID(event.app_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="app_user_id was not a valid UUID.",
        )

    event_repo = RevenueCatWebhookEventRepository(db)
    is_new_event = event_repo.record_if_new(
        event_id=event.id,
        event_type=event.type,
        user_id=user_id,
    )

    if not is_new_event:
        app_logger.info(f"Duplicate RevenueCat event {event.id} — skipping.")
        return {"processed": False, "duplicate": True}

    service = SubscriptionService(db)

    try:
        subscription = service.apply_revenuecat_event(
            user_id=user_id,
            event_type=event.type,
            product_id=event.product_id,
            purchased_at_ms=event.purchased_at_ms,
            expiration_at_ms=event.expiration_at_ms,
            provider_subscription_id=event.original_transaction_id or event.transaction_id,
        )
    except ValueError as exc:
        # Unrecognized product_id — a real config problem (a new
        # RevenueCat product was created without updating
        # PRODUCT_ID_TO_TIER), but NOT something RevenueCat should
        # keep retrying forever. Log loudly, still return 200.
        app_logger.error(f"RevenueCat event {event.id} could not be applied: {exc}")
        return {"processed": False, "error": str(exc)}

    if subscription is None:
        app_logger.warning(
            f"RevenueCat event {event.id} for app_user_id={user_id} — "
            f"no matching subscription found."
        )
        return {"processed": False, "reason": "no_subscription"}

    return {
        "processed": True,
        "tier": subscription.tier.value,
        "status": subscription.status.value,
    }