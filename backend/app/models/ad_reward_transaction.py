"""
=========================================================
AIMeals Backend
Ad Reward Transaction Model

Responsibilities:
    - Record each processed AdMob SSV callback's transaction_id,
      so a retried/replayed callback can be detected and rejected
      instead of double-granting bonus credits

Dependencies:
    - app.B_database.Base

Notes:
    - transaction_id has a UNIQUE constraint — this is what makes
      de-duplication atomic and race-safe. Rather than a Python-
      level "check if it exists, then insert" (which has the same
      class of race condition documented elsewhere in this
      codebase, e.g. SubscriptionRepository.try_increment_credits_used()),
      the repository simply attempts the INSERT and lets Postgres
      reject a duplicate transaction_id via the unique constraint.
      See AdRewardTransactionRepository.record_if_new().
    - user_id is stored for auditing/debugging (which user a given
      transaction belonged to) but is NOT part of the uniqueness
      constraint — transaction_id alone is Google's guarantee of
      per-reward-event uniqueness.
    - No relationship/back-reference to User is defined since this
      table is purely a write-once audit/dedup log, not something
      queried from the User side.

Example usage:
    from app.models.ad_reward_transaction import AdRewardTransaction

    txn = AdRewardTransaction(transaction_id="abc123", user_id=user.id)
=========================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.B_database import Base


class AdRewardTransaction(Base):
    """
    One row per successfully processed AdMob SSV callback.
    Existence of a row = "already processed, do not process again."

    Table: ad_reward_transactions
    """

    __tablename__ = "ad_reward_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # The de-duplication key. UNIQUE is what makes
    # AdRewardTransactionRepository.record_if_new() atomic — see
    # that method's docstring.
    transaction_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Stored for auditing only — not part of the uniqueness
    # constraint. Nullable in case a malformed callback's user_id
    # couldn't be parsed but we still want a record of the attempt
    # (repository/route layer decides whether to store in that case).
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
        return f"<AdRewardTransaction transaction_id={self.transaction_id} user_id={self.user_id}>"