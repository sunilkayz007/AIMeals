"""
=========================================================
AIMeals Backend
Achievement Repository

Responsibilities:
    - List every achievement definition, joined with whether
      (and when) the current user has earned it
    - Award an achievement to a user (idempotent — re-awarding
      an already-earned achievement is a safe no-op)
    - Mark earned achievements as "seen" once shown to the
      client

Dependencies:
    - app.models.achievement.AchievementDefinition
    - app.models.achievement.UserAchievement

Example usage:
    from app.repositories.achievement_repository import AchievementRepository

    repo = AchievementRepository(db)
    repo.award(user_id, "streak_7_day")   # idempotent
    rows = repo.list_for_user(user_id)    # definitions + earned status
=========================================================
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.achievement import AchievementDefinition, UserAchievement


class AchievementRepository:
    """
    Encapsulates all direct database access for
    AchievementDefinition and UserAchievement.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_definitions(self) -> List[AchievementDefinition]:
        return list(
            self.db.execute(
                select(AchievementDefinition).order_by(AchievementDefinition.sort_order)
            ).scalars()
        )

    def list_for_user(self, user_id: uuid.UUID) -> List[Tuple[AchievementDefinition, Optional[UserAchievement]]]:
        """
        Returns every achievement definition paired with this
        user's UserAchievement row if they've earned it, or None
        if not yet earned — one entry per definition, in
        sort_order, so the client can render a full locked/earned
        list without a second lookup.
        """
        definitions = self.list_definitions()
        earned_rows = {
            row.achievement_key: row
            for row in self.db.execute(
                select(UserAchievement).where(UserAchievement.user_id == user_id)
            ).scalars()
        }
        return [(d, earned_rows.get(d.key)) for d in definitions]

    def has_earned(self, user_id: uuid.UUID, achievement_key: str) -> bool:
        return (
            self.db.execute(
                select(UserAchievement).where(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_key == achievement_key,
                )
            ).scalar_one_or_none()
            is not None
        )

    def award(self, user_id: uuid.UUID, achievement_key: str) -> Optional[UserAchievement]:
        """
        Awards this achievement to this user. Idempotent via the
        same "attempt the insert, let the unique constraint reject
        a duplicate" pattern as AdRewardTransactionRepository
        (see that repository's docstring for the full reasoning) —
        safe to call every time a trigger condition is merely
        RE-CHECKED (e.g. every meal log), not just the one time it
        first becomes true.

        Returns the new UserAchievement row, or None if the user
        had already earned it (no-op, not an error).
        """
        row = UserAchievement(user_id=user_id, achievement_key=achievement_key)
        self.db.add(row)
        try:
            self.db.commit()
            self.db.refresh(row)
            return row
        except IntegrityError:
            self.db.rollback()
            return None

    def mark_seen(self, user_id: uuid.UUID, achievement_keys: List[str]) -> None:
        """
        Sets seen_at (if not already set) for the given earned
        achievements — called after GET /api/v1/achievements has
        returned them to the client once, so a second fetch
        doesn't re-flag them as new/unseen.
        """
        if not achievement_keys:
            return
        rows = self.db.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_key.in_(achievement_keys),
                UserAchievement.seen_at.is_(None),
            )
        ).scalars()
        now = datetime.now(timezone.utc)
        for row in rows:
            row.seen_at = now
        self.db.commit()
