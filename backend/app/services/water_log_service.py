"""
=========================================================
AIMeals Backend
Water Log Service

Responsibilities:
    - Log manual water entries
    - Compute the combined daily water summary: manual logs +
      food-derived water (from NutritionLog.water_ml), plus
      the "expected so far today" pacing comparison used by
      Home's water nudge

Dependencies:
    - app.repositories.water_log_repository.WaterLogRepository
    - app.repositories.nutrition_log_repository.NutritionLogRepository
    - app.repositories.profile_repository.ProfileRepository

Notes:
    - AWAKE_HOURS is a fixed, deliberately-not-per-user
      constant (14) — not derived from a real sleep-duration
      input. It's a product judgment call, not a researched
      figure the way e.g. 7-9 hours sleep is; discussed and
      set explicitly in the 2026-08-06 water-tracking design
      conversation. If this ever needs to be user-tunable,
      it'd move to a Profile column the same way
      typical_wake_time already is — deliberately NOT made
      one now, to keep the pacing formula simple until there's
      a real reason to vary it per user.
    - Pacing math: expected_so_far_ml = (daily_water_ml_target
      / AWAKE_HOURS) * hours_since(typical_wake_time). Both
      daily_water_ml_target and typical_wake_time must be set
      or pacing fields are simply omitted (None) — no silent
      fallback to a guessed target or guessed wake time.
    - pace_status thresholds are intentionally forgiving —
      "behind" only fires when actual intake is meaningfully
      under expected (see BEHIND_THRESHOLD_RATIO), not at the
      first sign of lagging, so the nudge doesn't feel naggy.

Example usage:
    from app.services.water_log_service import WaterLogService

    service = WaterLogService(db)
    service.log_water(user.id, date.today(), 250)
    summary = service.get_day_summary(user.id, date.today())
=========================================================
"""

import uuid
from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.nutrition_log_repository import NutritionLogRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.water_log_repository import WaterLogRepository

# See module docstring — a fixed product assumption, not a
# researched per-user figure.
AWAKE_HOURS = 14

# actual / expected must fall below this ratio for pace_status
# to report "behind" — keeps the nudge from firing on trivial
# gaps (e.g. 95% of expected still reads as "on_track").
BEHIND_THRESHOLD_RATIO = 0.75
AHEAD_THRESHOLD_RATIO = 1.15


# =========================================================
# Water Log Service
# =========================================================

class WaterLogService:
    def __init__(self, db: Session):
        self.db = db
        self.water_log_repo = WaterLogRepository(db)
        self.nutrition_log_repo = NutritionLogRepository(db)
        self.profile_repo = ProfileRepository(db)

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def log_water(self, user_id: uuid.UUID, logged_at: date, amount_ml: float):
        return self.water_log_repo.create(user_id, logged_at, amount_ml)

    def delete_water_log(self, log_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Deletes a water log entry, enforcing ownership. Silently
        no-ops if the log doesn't exist or belongs to someone
        else — matches this app's general "delete is idempotent
        from the caller's perspective" pattern elsewhere (e.g.
        remove_allergy), rather than raising for a state the
        user can't do anything about anyway.
        """
        log = self.water_log_repo.get_by_id(log_id)
        if log is not None and log.user_id == user_id:
            self.water_log_repo.delete(log)

    # ---------------------------------------------------
    # Read — Combined Daily Summary
    # ---------------------------------------------------

    def get_day_summary(self, user_id: uuid.UUID, target_date: date) -> dict:
        """
        Returns manual_ml, food_derived_ml, total_ml always;
        target_ml/expected_so_far_ml/pace_status only when the
        user has both daily_water_ml_target and
        typical_wake_time set AND target_date is today (pacing
        against "hours since wake" only makes sense for today —
        a past day is either fully in the books or doesn't
        apply).
        """
        manual_logs = self.water_log_repo.get_by_user_and_date(user_id, target_date)
        manual_ml = sum(log.amount_ml for log in manual_logs)

        nutrition_logs = self.nutrition_log_repo.get_by_user_and_date(user_id, target_date)
        food_derived_ml = sum(log.water_ml for log in nutrition_logs)

        total_ml = manual_ml + food_derived_ml

        profile = self.profile_repo.get_by_user_id(user_id)

        target_ml: Optional[float] = None
        expected_so_far_ml: Optional[float] = None
        pace_status: Optional[str] = None

        is_today = target_date == datetime.now(timezone.utc).date()

        # target_ml only needs the target itself — this was previously
        # bundled with the wake-time check below, which meant setting a
        # water target with no wake time silently never showed up
        # anywhere in the response. Pacing (expected_so_far_ml/
        # pace_status) is the part that genuinely needs wake_time, so
        # only that stays gated on it.
        if profile is not None and profile.daily_water_ml_target:
            target_ml = profile.daily_water_ml_target

            if profile.typical_wake_time and is_today:
                expected_so_far_ml = self._compute_expected_so_far(
                    target_ml, profile.typical_wake_time
                )

                if expected_so_far_ml is not None and expected_so_far_ml > 0:
                    ratio = total_ml / expected_so_far_ml
                    if ratio < BEHIND_THRESHOLD_RATIO:
                        pace_status = "behind"
                    elif ratio > AHEAD_THRESHOLD_RATIO:
                        pace_status = "ahead"
                    else:
                        pace_status = "on_track"

        return {
            "logged_at": target_date,
            "manual_ml": manual_ml,
            "food_derived_ml": food_derived_ml,
            "total_ml": total_ml,
            "target_ml": target_ml,
            "expected_so_far_ml": expected_so_far_ml,
            "pace_status": pace_status,
        }

    # ---------------------------------------------------
    # Internal Helper
    # ---------------------------------------------------

    def _compute_expected_so_far(
        self, daily_target_ml: float, typical_wake_time: str
    ) -> Optional[float]:
        """
        expected_so_far_ml = (daily_target_ml / AWAKE_HOURS) *
        hours_since(typical_wake_time), clamped to
        [0, daily_target_ml] — never negative (before wake time,
        clamped to 0) and never more than the full daily target
        (once AWAKE_HOURS have passed, "expected so far" is just
        "the whole target").

        typical_wake_time is stored as "HH:MM" (see Profile
        model). Returns None if it can't be parsed — a bad/blank
        stored value degrades to "no pacing shown" rather than
        crashing the request.
        """
        try:
            hour_str, minute_str = typical_wake_time.split(":")
            wake_time = time(hour=int(hour_str), minute=int(minute_str))
        except (ValueError, AttributeError):
            return None

        now = datetime.now(timezone.utc)
        wake_dt = datetime.combine(now.date(), wake_time, tzinfo=timezone.utc)

        if now < wake_dt:
            return 0.0

        hours_since_wake = (now - wake_dt).total_seconds() / 3600.0
        hours_since_wake = min(hours_since_wake, AWAKE_HOURS)

        per_hour_target = daily_target_ml / AWAKE_HOURS
        return round(per_hour_target * hours_since_wake, 1)