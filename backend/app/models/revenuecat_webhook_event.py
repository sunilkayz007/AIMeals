"""
=========================================================
AIMeals Backend
RevenueCat Webhook Event Model

Responsibilities:
    - Record each processed RevenueCat webhook event's id, so a
      retried delivery (RevenueCat retries on non-2xx responses,
      and can occasionally redeliver even successfully-processed
      events) can be detected and skipped instead of double-
      applying a subscription change

Dependencies:
    - app.B_database.Base

Notes:
    - Mirrors AdRewardTransaction's dedup pattern exactly: a
      UNIQUE constraint on event_id makes de-duplication atomic
      at the database level — see
      RevenueCatWebhookEventRepository.record_if_new().
    - event_type is stored alongside the id purely for auditing/
      debugging (so you can glance at this table and see what
      happened), not for any dedup logic.

Example usage:
    from app.models.revenuecat_webhook_event import RevenueCatWebhookEvent

    evt = RevenueCatWebhookEvent(event_id="abc123", event_type="RENEWAL", user_id=user.id)
=========================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.B_database import Base


class RevenueCatWebhookEvent(Base):
    """
    One row per successfully processed RevenueCat webhook event.
    Existence of a row = "already processed, do not process again."

    Table: revenuecat_webhook_events
    """

    __tablename__ = "revenuecat_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # RevenueCat's own event id. UNIQUE is what makes
    # RevenueCatWebhookEventRepository.record_if_new() atomic —
    # see that method's docstring.
    event_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<RevenueCatWebhookEvent event_id={self.event_id} type={self.event_type}>"