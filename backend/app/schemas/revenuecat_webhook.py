"""
=========================================================
AIMeals Backend
RevenueCat Webhook Schema

Responsibilities:
    - Define the shape of RevenueCat's webhook POST payload

Notes:
    - RevenueCat wraps every event in {"api_version": "1.0",
      "event": {...}} — this file mirrors that envelope.
    - Only the fields this app actually uses are modeled here.
      RevenueCat's real payload has many more fields (offer
      codes, tax/commission percentages, subscriber attributes,
      etc.) — everything not listed here is simply ignored by
      Pydantic (default model config elsewhere in this project
      is permissive about extra fields; this schema doesn't need
      to enumerate fields we don't act on).
    - id is RevenueCat's own event id, used for idempotency —
      see RevenueCatWebhookEventRepository.record_if_new(). Not
      to be confused with transaction_id (store-level purchase
      transaction) or original_transaction_id.
    - *_ms fields are epoch milliseconds, per RevenueCat's
      convention (note: milliseconds, not seconds — a common
      off-by-1000x bug if converted carelessly).
    - app_user_id is whatever identifier the RevenueCat SDK was
      configured with client-side — this app sets it to the
      AIMeals user's own UUID (as a string) at SDK init time, so
      it can be parsed straight into a uuid.UUID here.

Example usage:
    from app.schemas.revenuecat_webhook import RevenueCatWebhookPayload
=========================================================
"""

from typing import Optional

from pydantic import BaseModel


class RevenueCatEvent(BaseModel):
    id: str
    type: str
    app_user_id: str
    product_id: Optional[str] = None
    purchased_at_ms: Optional[int] = None
    expiration_at_ms: Optional[int] = None
    environment: Optional[str] = None
    store: Optional[str] = None
    transaction_id: Optional[str] = None
    original_transaction_id: Optional[str] = None


class RevenueCatWebhookPayload(BaseModel):
    api_version: str
    event: RevenueCatEvent