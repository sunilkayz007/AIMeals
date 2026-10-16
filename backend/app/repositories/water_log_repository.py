"""
=========================================================
AIMeals Backend
Water Log Repository

Responsibilities:
    - Perform CRUD operations against the water_logs table
    - Contains NO business logic

Example usage:
    from app.repositories.water_log_repository import WaterLogRepository

    repo = WaterLogRepository(db)
    todays_logs = repo.get_by_user_and_date(user.id, date.today())
=========================================================
"""

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.water_log import WaterLog


# =========================================================
# Water Log Repository
# =========================================================

class WaterLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_and_date(self, user_id: uuid.UUID, target_date: date) -> List[WaterLog]:
        return (
            self.db.query(WaterLog)
            .filter(WaterLog.user_id == user_id, WaterLog.logged_at == target_date)
            .order_by(WaterLog.created_at.asc())
            .all()
        )

    def get_by_id(self, log_id: uuid.UUID) -> Optional[WaterLog]:
        return self.db.query(WaterLog).filter(WaterLog.id == log_id).first()

    def create(self, user_id: uuid.UUID, logged_at: date, amount_ml: float) -> WaterLog:
        new_log = WaterLog(user_id=user_id, logged_at=logged_at, amount_ml=amount_ml)
        self.db.add(new_log)
        self.db.commit()
        self.db.refresh(new_log)
        return new_log

    def delete(self, log: WaterLog) -> None:
        self.db.delete(log)
        self.db.commit()