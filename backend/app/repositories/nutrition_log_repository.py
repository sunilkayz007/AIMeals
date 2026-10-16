"""
=========================================================
AIMeals Backend
Nutrition Log Repository

Responsibilities:
    - Perform CRUD operations against the nutrition_logs table
    - Contains NO business logic

Dependencies:
    - app.models.nutrition_log.NutritionLog

Example usage:
    from app.repositories.nutrition_log_repository import NutritionLogRepository

    repo = NutritionLogRepository(db)
    todays_logs = repo.get_by_user_and_date(user.id, date.today())
=========================================================
"""

import uuid
from datetime import date, datetime
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.models.nutrition_log import MealType, NutritionLog


# =========================================================
# Nutrition Log Repository
# =========================================================

class NutritionLogRepository:
    """
    Encapsulates all direct database access for the NutritionLog model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_id(self, log_id: uuid.UUID) -> Optional[NutritionLog]:
        return self.db.query(NutritionLog).filter(NutritionLog.id == log_id).first()

    def get_by_user(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[NutritionLog]:
        """
        Returns a user's logs, optionally filtered to a date range.
        If start_date/end_date are omitted, returns all logs.
        """
        query = self.db.query(NutritionLog).filter(NutritionLog.user_id == user_id)

        if start_date is not None:
            query = query.filter(NutritionLog.logged_at >= start_date)
        if end_date is not None:
            query = query.filter(NutritionLog.logged_at <= end_date)

        return query.order_by(NutritionLog.logged_at.desc()).all()

    def get_by_user_and_date(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> List[NutritionLog]:
        """Returns all of a user's log entries for a single specific date."""
        return (
            self.db.query(NutritionLog)
            .filter(
                NutritionLog.user_id == user_id,
                NutritionLog.logged_at == target_date,
            )
            .all()
        )

    def get_logged_recipe_ids(self, user_id: uuid.UUID) -> Set[uuid.UUID]:
        """
        Returns the set of recipe_id values that already have AT
        LEAST ONE log entry for this user. Used by
        get_pending_confirmations() to exclude recipes that have
        already been logged (in full or in part) from the "did
        you eat this?" prompt list — logging it once, even
        partially, counts as "already asked and answered."
        """
        rows = (
            self.db.query(NutritionLog.recipe_id)
            .filter(
                NutritionLog.user_id == user_id,
                NutritionLog.recipe_id.isnot(None),
            )
            .distinct()
            .all()
        )
        return {row[0] for row in rows}

    def get_logged_food_image_ids(self, user_id: uuid.UUID) -> Set[uuid.UUID]:
        """Same purpose as get_logged_recipe_ids(), for food-image scans."""
        rows = (
            self.db.query(NutritionLog.food_image_id)
            .filter(
                NutritionLog.user_id == user_id,
                NutritionLog.food_image_id.isnot(None),
            )
            .distinct()
            .all()
        )
        return {row[0] for row in rows}

    def get_distinct_logged_dates(self, user_id: uuid.UUID, limit_days: int = 40) -> List[date]:
        """
        Returns this user's distinct logged_at dates, most recent
        first, capped at limit_days rows -- used by
        AchievementService.check_and_award_streaks() to compute
        the current consecutive-day logging streak without pulling
        every individual meal row (a day with 3 logged meals only
        needs to count once for streak purposes).

        limit_days=40 comfortably covers the longest seeded streak
        achievement (30 days) with a little headroom, while keeping
        the query bounded rather than scanning a power user's
        entire history every time a meal is logged.
        """
        rows = (
            self.db.query(NutritionLog.logged_at)
            .filter(NutritionLog.user_id == user_id)
            .distinct()
            .order_by(NutritionLog.logged_at.desc())
            .limit(limit_days)
            .all()
        )
        return [row[0] for row in rows]

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        logged_at: date,
        meal_type: MealType,
        food_name: str,
        calories: float,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
        fiber_g: float = 0.0,
        water_ml: float = 0.0,
        micronutrients: Optional[dict] = None,
        recipe_id: Optional[uuid.UUID] = None,
        food_image_id: Optional[uuid.UUID] = None,
        portion_percentage: float = 100.0,
        notes: Optional[str] = None,
    ) -> NutritionLog:
        new_log = NutritionLog(
            user_id=user_id,
            recipe_id=recipe_id,
            food_image_id=food_image_id,
            logged_at=logged_at,
            meal_type=meal_type,
            food_name=food_name,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            fiber_g=fiber_g,
            water_ml=water_ml,
            micronutrients=micronutrients,
            portion_percentage=portion_percentage,
            notes=notes,
        )

        self.db.add(new_log)
        self.db.commit()
        self.db.refresh(new_log)

        return new_log

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update(self, log: NutritionLog, **fields) -> NutritionLog:
        for key, value in fields.items():
            setattr(log, key, value)

        self.db.commit()
        self.db.refresh(log)

        return log

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete(self, log: NutritionLog) -> None:
        self.db.delete(log)
        self.db.commit()
