"""
=========================================================
AIMeals Backend
Profile Schemas

Responsibilities:
    - Define request/response shapes for profile, allergy,
      and dietary restriction data

Dependencies:
    - app.models.profile (Gender, ActivityLevel, Goal)
    - app.models.allergy (AllergySeverity)

Example usage:
    from app.schemas.profile import ProfileUpdate, ProfileOut

    def update_profile(payload: ProfileUpdate):
        ...
=========================================================
"""

import uuid
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.allergy import AllergySeverity
from app.models.profile import ActivityLevel, Gender, Goal


# =========================================================
# Request Schema — Create/Update Profile
# =========================================================

class ProfileUpdate(BaseModel):
    """
    Shape of the payload accepted by PUT /profile.

    All fields optional — only fields explicitly provided
    are applied, matching ProfileService.create_or_update_profile()'s
    partial-update semantics. Used for both the user's very
    first profile save and any later edit.
    """

    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[ActivityLevel] = None
    goal: Optional[Goal] = None
    daily_calorie_target: Optional[float] = None
    protein_g_target: Optional[float] = None
    carbs_g_target: Optional[float] = None
    fat_g_target: Optional[float] = None
    fiber_g_target: Optional[float] = None
    daily_water_ml_target: Optional[float] = None
    typical_wake_time: Optional[str] = None
    region_code: Optional[str] = None


# =========================================================
# Response Schema — Profile
# =========================================================

class ProfileOut(BaseModel):
    """
    Shape of profile data returned to the client.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[ActivityLevel] = None
    goal: Optional[Goal] = None
    daily_calorie_target: Optional[float] = None
    protein_g_target: Optional[float] = None
    carbs_g_target: Optional[float] = None
    fat_g_target: Optional[float] = None
    fiber_g_target: Optional[float] = None
    daily_water_ml_target: Optional[float] = None
    typical_wake_time: Optional[str] = None
    region_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# Request Schema — Add Allergy
# =========================================================

class AllergyCreate(BaseModel):
    """
    Shape of the payload accepted by POST /profile/allergies.

    allergy_name is free text — ProfileService creates the
    allergy in the master lookup table if it doesn't already
    exist, so the client doesn't need to know the master list
    in advance.
    """

    allergy_name: str
    severity: AllergySeverity = AllergySeverity.MODERATE

    @field_validator("allergy_name")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("allergy_name cannot be blank.")
        return value.strip()


# =========================================================
# Response Schema — Allergy
# =========================================================

class AllergyOut(BaseModel):
    """
    Shape of a user's linked allergy, flattened for the
    client — combines the UserAllergy junction row with the
    linked Allergy's name so the client doesn't need a
    second lookup.

    Built manually in the controller (not via model_validate)
    since allergy_name comes from the related Allergy object,
    not a direct attribute of UserAllergy.
    """

    id: uuid.UUID
    allergy_id: uuid.UUID
    allergy_name: str
    severity: AllergySeverity


# =========================================================
# Request Schema — Add Dietary Restriction
# =========================================================

class DietaryRestrictionCreate(BaseModel):
    """
    Shape of the payload accepted by POST /profile/dietary-restrictions.
    """

    restriction_name: str

    @field_validator("restriction_name")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("restriction_name cannot be blank.")
        return value.strip()


# =========================================================
# Response Schema — Dietary Restriction
# =========================================================

class DietaryRestrictionOut(BaseModel):
    """
    Same flattening approach as AllergyOut — built manually
    in the controller from the UserDietaryRestriction +
    DietaryRestriction pair.
    """

    id: uuid.UUID
    restriction_id: uuid.UUID
    restriction_name: str


# =========================================================
# Response Schema — Combined Dietary Profile View
# =========================================================

class FullDietaryProfileOut(BaseModel):
    """
    Shape returned by GET /profile/full — profile, allergies,
    and dietary restrictions together. Mirrors
    ProfileService.get_full_dietary_profile(), since AI
    features almost always need all three at once.
    """

    profile: Optional[ProfileOut] = None
    allergies: List[AllergyOut] = []
    dietary_restrictions: List[DietaryRestrictionOut] = []


# =========================================================
# Response Schema — RDA-Based Nutrient Targets
# =========================================================

class RDATargetOut(BaseModel):
    """
    One computed nutrient target — see app.core.rda for the
    calculation. kind is "goal" (reach this amount) or
    "limit" (stay under this amount — currently only sodium).
    """

    amount: float
    unit: str
    kind: Literal["goal", "limit"]


class RDATargetsOut(BaseModel):
    """
    Shape returned by GET /profile/rda-targets — the 10
    auto-computed mineral/vitamin targets, keyed by nutrient.
    disclaimer is a fixed one-line note the client displays
    alongside these values (see app.core.rda's module
    docstring on why these are general population averages,
    not personalized medical guidance).
    """

    sodium_mg: RDATargetOut
    potassium_mg: RDATargetOut
    calcium_mg: RDATargetOut
    iron_mg: RDATargetOut
    magnesium_mg: RDATargetOut
    zinc_mg: RDATargetOut
    vitamin_a_mcg: RDATargetOut
    vitamin_b12_mcg: RDATargetOut
    vitamin_c_mg: RDATargetOut
    vitamin_d_mcg: RDATargetOut
    disclaimer: str