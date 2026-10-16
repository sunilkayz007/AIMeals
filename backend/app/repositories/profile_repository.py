"""
=========================================================
AIMeals Backend
Profile Repository

Responsibilities:
    - Perform CRUD operations against the profiles table
    - Contains NO business logic

Dependencies:
    - app.models.profile.Profile

Example usage:
    from app.repositories.profile_repository import ProfileRepository

    repo = ProfileRepository(db)
    profile = repo.get_by_user_id(user.id)
=========================================================
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.profile import ActivityLevel, Gender, Goal, Profile


# =========================================================
# Profile Repository
# =========================================================

class ProfileRepository:
    """
    Encapsulates all direct database access for the Profile model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Profile]:
        return self.db.query(Profile).filter(Profile.user_id == user_id).first()

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        date_of_birth=None,
        gender: Optional[Gender] = None,
        height_cm: Optional[float] = None,
        weight_kg: Optional[float] = None,
        activity_level: Optional[ActivityLevel] = None,
        goal: Optional[Goal] = None,
        daily_calorie_target: Optional[float] = None,
        protein_g_target: Optional[float] = None,
        carbs_g_target: Optional[float] = None,
        fat_g_target: Optional[float] = None,
        fiber_g_target: Optional[float] = None,
        daily_water_ml_target: Optional[float] = None,
        typical_wake_time: Optional[str] = None,
        region_code: Optional[str] = None,
    ) -> Profile:
        """
        Creates a new profile for a user.
        All fields except user_id are optional, since a
        profile can be created incrementally.
        """
        new_profile = Profile(
            user_id=user_id,
            date_of_birth=date_of_birth,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            activity_level=activity_level,
            goal=goal,
            daily_calorie_target=daily_calorie_target,
            protein_g_target=protein_g_target,
            carbs_g_target=carbs_g_target,
            fat_g_target=fat_g_target,
            fiber_g_target=fiber_g_target,
            daily_water_ml_target=daily_water_ml_target,
            typical_wake_time=typical_wake_time,
            region_code=region_code,
        )

        self.db.add(new_profile)
        self.db.commit()
        self.db.refresh(new_profile)

        return new_profile

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update(self, profile: Profile, **fields) -> Profile:
        """
        Updates arbitrary fields on an existing profile.

        Usage:
            repo.update(profile, weight_kg=73.5, goal=Goal.MAINTENANCE)
        """
        for key, value in fields.items():
            setattr(profile, key, value)

        self.db.commit()
        self.db.refresh(profile)

        return profile