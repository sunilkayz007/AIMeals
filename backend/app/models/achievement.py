"""
=========================================================
AIMeals Backend
Achievement Models

Responsibilities:
    - Define the achievements a user can earn
      (AchievementDefinition — seed data, not user-editable)
      and record which ones a given user has actually earned
      (UserAchievement)

Dependencies:
    - app.B_database.Base

Notes:
    - Part of the Coach roadmap's Part 2 (see
      Claude outputs/coach-roadmap-plan.md). This first phase
      seeds ONLY the 3 logging-streak definitions (see this
      migration in p2k3l4m5n6o7_add_coach_memory_and_achievements.py)
      — first-time-milestone achievements (first recipe, first
      health report, etc.) are an explicitly deferred follow-up
      per the plan's own suggested build order, not built yet.
    - AchievementDefinition.key is the primary key (a short
      stable string like "streak_7_day") rather than a surrogate
      UUID — these rows are seed data referenced by code
      (AchievementService), so a human-readable stable key is
      more useful than a UUID here.
    - UserAchievement is unique on (user_id, achievement_key) —
      earned once, never re-earned or duplicated. seen_at is
      nullable and set the first time GET /api/v1/achievements
      returns this row to the client — doubles as a lightweight
      "new/unseen" flag without a separate notifications table.

Example usage:
    from app.models.achievement import AchievementDefinition, UserAchievement
=========================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.B_database import Base


class AchievementDefinition(Base):
    """
    Seed data describing one achievement a user can earn.
    Not user-editable — rows come only from migrations.

    Table: achievement_definitions
    """

    __tablename__ = "achievement_definitions"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(10), nullable=False)

    # "streak" | "count" | "milestone" — currently only "streak" is
    # seeded/checked (AchievementService.check_and_award_streaks()).
    # The other two values are reserved for the deferred
    # first-time-milestone follow-up phase.
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<AchievementDefinition key={self.key}>"


class UserAchievement(Base):
    """
    One row per achievement a specific user has actually earned.

    Table: user_achievements
    """

    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_key", name="uq_user_achievements_user_id_achievement_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    achievement_key: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("achievement_definitions.key", ondelete="CASCADE"),
        nullable=False,
    )

    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Null until the client has been shown this unlock once (set by
    # AchievementRepository.mark_seen() the first time
    # GET /api/v1/achievements returns it) — see this file's module
    # docstring.
    seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<UserAchievement user_id={self.user_id} achievement_key={self.achievement_key}>"
