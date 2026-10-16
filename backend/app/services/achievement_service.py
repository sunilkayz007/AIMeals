"""
=========================================================
AIMeals Backend
Achievement Service

Responsibilities:
    - Compute a user's current daily-logging streak and award
      any newly-qualifying streak achievement
    - Assemble the full achievement list (definitions + this
      user's earned status) for the Achievements screen

Dependencies:
    - app.repositories.achievement_repository.AchievementRepository
    - app.repositories.nutrition_log_repository.NutritionLogRepository

Notes:
    - This is Part 2 of the Coach roadmap (see
      Claude outputs/coach-roadmap-plan.md), scoped to exactly
      that plan's own suggested build order step 4: logging-
      streak triggers ONLY. First-time-milestone achievements
      (first recipe generated, first health report uploaded,
      etc.) are explicitly deferred to a later step, per the
      plan's own phasing -- not built here.
    - check_and_award_streaks() is designed to be called every
      time a meal is logged (cheapest approach per the plan --
      no separate polling job) and is idempotent: re-checking an
      already-earned streak is a safe no-op via
      AchievementRepository.award()'s unique-constraint-based
      de-duplication.
    - Streak semantics: consecutive CALENDAR days (relative to
      today, not to whatever date was just logged) with at least
      one meal logged. A backfilled log for a past date can still
      complete today's streak if it fills a gap, but logging only
      old dates without today does not itself award anything --
      matches the everyday intuition of a "daily streak."

Example usage:
    from app.services.achievement_service import AchievementService

    service = AchievementService(db)
    newly_awarded = service.check_and_award_streaks(user_id)
=========================================================
"""

import uuid
from datetime import date, timedelta
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.repositories.achievement_repository import AchievementRepository
from app.repositories.nutrition_log_repository import NutritionLogRepository

# (streak length in days, achievement key) -- must match the keys
# seeded in migration p2k3l4m5n6o7_add_coach_memory_and_achievements.py.
STREAK_THRESHOLDS: List[Tuple[int, str]] = [
    (3, "streak_3_day"),
    (7, "streak_7_day"),
    (30, "streak_30_day"),
]


class AchievementService:
    def __init__(self, db: Session):
        self.db = db
        self.achievement_repo = AchievementRepository(db)
        self.log_repo = NutritionLogRepository(db)

    def check_and_award_streaks(self, user_id: uuid.UUID) -> List[str]:
        """
        Computes the user's current consecutive-day logging streak
        and awards any threshold it now meets or exceeds. Safe to
        call unconditionally after every meal log -- already-earned
        achievements are silently skipped (idempotent), so this
        never needs to track "have I already checked this."

        Returns the list of achievement_keys newly awarded by THIS
        call (empty list if none, which is the common case).
        """
        streak_length = self._compute_current_streak(user_id)

        newly_awarded: List[str] = []
        for threshold, key in STREAK_THRESHOLDS:
            if streak_length < threshold:
                continue
            awarded_row = self.achievement_repo.award(user_id, key)
            if awarded_row is not None:
                newly_awarded.append(key)

        return newly_awarded

    def get_achievements_for_user(self, user_id: uuid.UUID) -> List[dict]:
        """
        Returns every achievement definition combined with this
        user's earned status, in display order. Marks any
        not-yet-seen earned achievements as seen as a side effect
        (matches GET /api/v1/achievements's documented "seen on
        fetch" contract) -- so this method is intended to be
        called at most once per client-visible page load, not
        polled silently in the background.
        """
        pairs = self.achievement_repo.list_for_user(user_id)

        results = []
        newly_seen_keys = []
        for definition, earned_row in pairs:
            is_new = earned_row is not None and earned_row.seen_at is None
            if is_new:
                newly_seen_keys.append(definition.key)
            results.append(
                {
                    "key": definition.key,
                    "title": definition.title,
                    "description": definition.description,
                    "icon": definition.icon,
                    "earned": earned_row is not None,
                    "earned_at": earned_row.earned_at if earned_row else None,
                    "is_new": is_new,
                }
            )

        if newly_seen_keys:
            self.achievement_repo.mark_seen(user_id, newly_seen_keys)

        return results

    def _compute_current_streak(self, user_id: uuid.UUID) -> int:
        logged_dates = set(self.log_repo.get_distinct_logged_dates(user_id))

        streak = 0
        cursor = date.today()
        while cursor in logged_dates:
            streak += 1
            cursor -= timedelta(days=1)

        return streak
