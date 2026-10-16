"""
=========================================================
AIMeals Backend
Daily Tip Repository

Responsibilities:
    - Read/create daily_tips rows
    - Contains NO business logic

Dependencies:
    - app.models.daily_tip.DailyTip

Example usage:
    from app.repositories.daily_tip_repository import DailyTipRepository

    repo = DailyTipRepository(db)
    existing = repo.get_for_user_and_date(user.id, date.today())
=========================================================
"""

import uuid
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.daily_tip import DailyTip


# =========================================================
# Daily Tip Repository
# =========================================================

class DailyTipRepository:
    """
    Encapsulates all direct database access for the DailyTip model.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_for_user_and_date(self, user_id: uuid.UUID, tip_date: date) -> Optional[DailyTip]:
        return (
            self.db.query(DailyTip)
            .filter(DailyTip.user_id == user_id, DailyTip.tip_date == tip_date)
            .first()
        )

    def create(self, user_id: uuid.UUID, tip_date: date, tip_text: str) -> DailyTip:
        new_tip = DailyTip(user_id=user_id, tip_date=tip_date, tip_text=tip_text)
        self.db.add(new_tip)
        self.db.commit()
        self.db.refresh(new_tip)
        return new_tip