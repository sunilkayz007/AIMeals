"""
=========================================================
AIMeals Backend
RevenueCat Webhook Event Repository

Responsibilities:
    - Atomically record a RevenueCat webhook event's id,
      rejecting duplicates via the database's unique constraint

Dependencies:
    - app.models.revenuecat_webhook_event.RevenueCatWebhookEvent

Example usage:
    from app.repositories.revenuecat_webhook_event_repository import (
        RevenueCatWebhookEventRepository,
    )

    repo = RevenueCatWebhookEventRepository(db)
    is_new = repo.record_if_new(event_id, event_type, user_id)
    if not is_new:
        # duplicate/redelivered event, do not apply again
        ...
=========================================================
"""

import uuid
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.revenuecat_webhook_event import RevenueCatWebhookEvent


class RevenueCatWebhookEventRepository:
    """
    Encapsulates all direct database access for the
    RevenueCatWebhookEvent model.
    """

    def __init__(self, db: Session):
        self.db = db

    def record_if_new(
        self,
        event_id: str,
        event_type: str,
        user_id: Optional[uuid.UUID],
    ) -> bool:
        """
        Attempts to insert a new RevenueCatWebhookEvent row for
        this event_id.

        Same atomic pattern as
        AdRewardTransactionRepository.record_if_new(): attempts
        the INSERT and lets the database's UNIQUE constraint on
        event_id be the source of truth, rather than a Python-
        level check-then-write.

        Returns:
            True if this event_id was new (row inserted, safe to
                proceed with applying the subscription change).
            False if this event_id was already recorded
                (duplicate/redelivered event — caller must NOT
                apply the change again).
        """
        event_record = RevenueCatWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            user_id=user_id,
        )
        self.db.add(event_record)

        try:
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False