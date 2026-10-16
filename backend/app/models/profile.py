"""
=========================================================
AIMeals Backend
Profile Model

Responsibilities:
    - Define the profiles table schema
    - Define Gender, ActivityLevel, and Goal enums

Dependencies:
    - app.B_database.Base
    - app.models.user.User (one-to-one FK target)

Notes:
    - weight_kg here is CURRENT weight only. Historical
      weight tracking over time belongs in the Progress
      model (Phase 5, later module), not here.
    - Age is not stored directly; compute it from
      date_of_birth when needed, since stored age would
      go stale.
    - UPDATED: protein_g_target/carbs_g_target/fat_g_target/
      fiber_g_target are manually-set macro goals, same
      simple pattern as daily_calorie_target — NOT the
      planned AI-computed macro-target feature (a separate,
      bigger project still not built). These exist so the
      Home screen's progress rings/cards can show real
      consumed-vs-target data for macros, not just calories,
      without waiting on that AI feature.

Example usage:
    from app.models.profile import Profile, Gender, ActivityLevel, Goal

    profile = Profile(
        user_id=user.id,
        date_of_birth=date(1995, 4, 12),
        gender=Gender.MALE,
        height_cm=175.0,
        weight_kg=72.5,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=Goal.WEIGHT_LOSS,
    )
=========================================================
"""

import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Enums
# =========================================================

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class ActivityLevel(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTRA_ACTIVE = "extra_active"


class Goal(str, enum.Enum):
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"


# =========================================================
# Profile Model
# =========================================================

class Profile(Base):
    """
    Represents a user's nutrition/fitness profile.

    Table: profiles
    One-to-one with User.
    """

    __tablename__ = "profiles"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Foreign Key (one-to-one)
    # ---------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------
    # Physical Stats
    # ---------------------------------------------------

    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    gender: Mapped[Optional[Gender]] = mapped_column(
        Enum(Gender, name="gender"),
        nullable=True,
    )

    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ---------------------------------------------------
    # Activity / Goals
    # ---------------------------------------------------

    activity_level: Mapped[Optional[ActivityLevel]] = mapped_column(
        Enum(ActivityLevel, name="activity_level"),
        nullable=True,
    )

    goal: Mapped[Optional[Goal]] = mapped_column(
        Enum(Goal, name="goal"),
        nullable=True,
    )

    daily_calorie_target: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # Manually-set macro goals — same simple pattern as
    # daily_calorie_target above. See module docstring for why
    # this is deliberately NOT the AI-computed macro-target
    # feature.
    protein_g_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carbs_g_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fat_g_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Added alongside the Home screen's 6-card "Today at a glance"
    # redesign (Aug 2026) — same manually-set pattern as the other
    # macro targets above, not the AI-computed feature.
    fiber_g_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ---------------------------------------------------
    # Water Tracking (added 2026-08-06)
    # ---------------------------------------------------

    daily_water_ml_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Used to pace the "expected water intake so far today" nudge
    # on Home — expected_so_far = daily_water_ml_target / 14 (fixed
    # assumed awake-hours constant, see WaterLogService) * hours
    # since this time. Time-only (no date), stored as a plain
    # HH:MM string rather than a Time column to sidestep timezone
    # handling for something that's really "a rough daily habit,"
    # not a precise timestamp. Nullable — the pacing nudge simply
    # doesn't show until the user sets this (Settings/Goals).
    typical_wake_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)

    # ---------------------------------------------------
    # Regional Context (added Aug 2026)
    # ---------------------------------------------------

    # Two-letter ISO region code (e.g. "IN", "US"), read from the
    # device's own configured locale on the frontend (via
    # expo-localization) -- NOT live GPS, NOT a manual "select your
    # country" step, no location permission of any kind. Used only
    # as a SOFT regional hint for recipe/meal-plan/coach generation
    # (see AIService._build_region_context()) -- favors locally
    # available ingredients/dishes without being rigid about it, and
    # is never surfaced as a user-facing setting.
    region_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user = relationship("User")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<Profile id={self.id} user_id={self.user_id} goal={self.goal}>"