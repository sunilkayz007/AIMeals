"""
=========================================================
AIMeals Backend
Ad Reward Transaction Repository

Responsibilities:
    - Atomically record an AdMob SSV callback's transaction_id,
      rejecting duplicates via the database's unique constraint

Dependencies:
    - app.models.ad_reward_transaction.AdRewardTransaction

Example usage:
    from app.repositories.ad_reward_transaction_repository import (
        AdRewardTransactionRepository,
    )

    repo = AdRewardTransactionRepository(db)
    is_new = repo.record_if_new(transaction_id, user_id)
    if not is_new:
        # duplicate callback, do not grant credits again
        ...
=========================================================
"""

import uuid
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ad_reward_transaction import AdRewardTransaction


class AdRewardTransactionRepository:
    """
    Encapsulates all direct database access for the
    AdRewardTransaction model.
    """

    def __init__(self, db: Session):
        self.db = db

    def record_if_new(
        self,
        transaction_id: str,
        user_id: Optional[uuid.UUID],
    ) -> bool:
        """
        Attempts to insert a new AdRewardTransaction row for this
        transaction_id.

        This is the atomic de-duplication check: rather than
        querying "does this transaction_id already exist?" and
        then inserting (a plain Python-level check-then-write,
        which has the same race-condition shape documented
        elsewhere in this codebase for credit consumption), this
        just ATTEMPTS the insert and lets the database's own
        UNIQUE constraint on transaction_id be the source of
        truth. Two near-simultaneous callbacks with the same
        transaction_id will have exactly one INSERT succeed; the
        other raises IntegrityError and is caught here.

        Returns:
            True if this transaction_id was new (row inserted,
                safe to proceed with granting credits).
            False if this transaction_id was already recorded
                (duplicate/replayed callback — caller must NOT
                grant credits again).
        """
        transaction = AdRewardTransaction(
            transaction_id=transaction_id,
            user_id=user_id,
        )
        self.db.add(transaction)

        try:
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False