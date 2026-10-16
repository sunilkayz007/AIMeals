"""
=========================================================
AIMeals Backend
Profile Controller

Responsibilities:
    - Orchestrate calls to ProfileService
    - Translate framework-agnostic service exceptions into
      HTTPException with correct status codes
    - Convert SQLAlchemy models into Pydantic response schemas

Dependencies:
    - app.services.profile_service.ProfileService
    - app.core.exceptions

Notes:
    - Controllers contain NO business logic. They orchestrate
      and translate only. All actual logic lives in the
      service layer.
    - AllergyOut/DietaryRestrictionOut are built manually
      here (not via model_validate) since their flattened
      *_name fields come from a related object (link.allergy.name,
      link.restriction.name), not a direct attribute.
    - get_rda_targets() catches a plain ValueError from the
      service (raised when the user has no profile yet, or
      no date_of_birth set) and maps it to a 400 — this is a
      normal "complete your profile first" state, not a
      system failure.
=========================================================
"""

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateAllergyError, DuplicateRestrictionError
from app.schemas.profile import (
    AllergyCreate,
    AllergyOut,
    DietaryRestrictionCreate,
    DietaryRestrictionOut,
    FullDietaryProfileOut,
    ProfileOut,
    ProfileUpdate,
    RDATargetOut,
    RDATargetsOut,
)
from app.services.profile_service import ProfileService


# =========================================================
# Profile Controller
# =========================================================

class ProfileController:
    """
    Thin orchestration layer between API routes and ProfileService.
    """

    def __init__(self, db: Session):
        self.service = ProfileService(db)

    # ---------------------------------------------------
    # Profile
    # ---------------------------------------------------

    def get_profile(self, user_id: uuid.UUID) -> ProfileOut | None:
        """
        Returns None (not a 404) if the user hasn't created a
        profile yet — matching ProfileService's own treatment
        of "no profile" as a normal state, not an error.
        """
        profile = self.service.get_profile(user_id)
        if profile is None:
            return None
        return ProfileOut.model_validate(profile)

    def update_profile(self, user_id: uuid.UUID, payload: ProfileUpdate) -> ProfileOut:
        profile = self.service.create_or_update_profile(
            user_id=user_id,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            activity_level=payload.activity_level,
            goal=payload.goal,
            daily_calorie_target=payload.daily_calorie_target,
            protein_g_target=payload.protein_g_target,
            carbs_g_target=payload.carbs_g_target,
            fat_g_target=payload.fat_g_target,
            fiber_g_target=payload.fiber_g_target,
            daily_water_ml_target=payload.daily_water_ml_target,
            typical_wake_time=payload.typical_wake_time,
            region_code=payload.region_code,
        )
        return ProfileOut.model_validate(profile)

    # ---------------------------------------------------
    # IP-Based Region Detection
    # ---------------------------------------------------

    def detect_region(self, user_id: uuid.UUID, client_ip: str) -> Optional[str]:
        """
        Resolves the caller's IP to a country code and saves it to
        their profile if changed -- see
        ProfileService.detect_and_save_region()'s docstring. No
        error is ever raised here: a failed/unresolvable lookup
        just returns None, which the route maps to a plain
        {"region_code": null} response, not an error.
        """
        return self.service.detect_and_save_region(user_id, client_ip)

    # ---------------------------------------------------
    # RDA-Based Nutrient Targets
    # ---------------------------------------------------

    def get_rda_targets(self, user_id: uuid.UUID) -> RDATargetsOut:
        """
        Returns the 10 auto-computed mineral/vitamin targets
        for this user, based on their stored age/gender/weight.

        Raises:
            HTTPException 400: the user has no profile yet, or
                their profile has no date_of_birth set — see
                ProfileService.get_rda_targets()'s docstring.
        """
        try:
            targets = self.service.get_rda_targets(user_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        return RDATargetsOut(
            sodium_mg=RDATargetOut(**targets["sodium_mg"].__dict__),
            potassium_mg=RDATargetOut(**targets["potassium_mg"].__dict__),
            calcium_mg=RDATargetOut(**targets["calcium_mg"].__dict__),
            iron_mg=RDATargetOut(**targets["iron_mg"].__dict__),
            magnesium_mg=RDATargetOut(**targets["magnesium_mg"].__dict__),
            zinc_mg=RDATargetOut(**targets["zinc_mg"].__dict__),
            vitamin_a_mcg=RDATargetOut(**targets["vitamin_a_mcg"].__dict__),
            vitamin_b12_mcg=RDATargetOut(**targets["vitamin_b12_mcg"].__dict__),
            vitamin_c_mg=RDATargetOut(**targets["vitamin_c_mg"].__dict__),
            vitamin_d_mcg=RDATargetOut(**targets["vitamin_d_mcg"].__dict__),
            disclaimer=targets["disclaimer"],
        )

    # ---------------------------------------------------
    # Allergies
    # ---------------------------------------------------

    def add_allergy(self, user_id: uuid.UUID, payload: AllergyCreate) -> None:
        try:
            self.service.add_allergy(user_id, payload.allergy_name, payload.severity)
        except DuplicateAllergyError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

    def remove_allergy(self, user_id: uuid.UUID, allergy_id: uuid.UUID) -> None:
        # Idempotent by design (matches ProfileService.remove_allergy) —
        # no error if the link doesn't exist.
        self.service.remove_allergy(user_id, allergy_id)

    # ---------------------------------------------------
    # Dietary Restrictions
    # ---------------------------------------------------

    def add_dietary_restriction(self, user_id: uuid.UUID, payload: DietaryRestrictionCreate) -> None:
        try:
            self.service.add_dietary_restriction(user_id, payload.restriction_name)
        except DuplicateRestrictionError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

    def remove_dietary_restriction(self, user_id: uuid.UUID, restriction_id: uuid.UUID) -> None:
        self.service.remove_dietary_restriction(user_id, restriction_id)

    # ---------------------------------------------------
    # Combined View
    # ---------------------------------------------------

    def get_full_dietary_profile(self, user_id: uuid.UUID) -> FullDietaryProfileOut:
        result = self.service.get_full_dietary_profile(user_id)

        profile_out = (
            ProfileOut.model_validate(result["profile"])
            if result["profile"] is not None
            else None
        )

        allergies_out = [
            AllergyOut(
                id=link.id,
                allergy_id=link.allergy_id,
                allergy_name=link.allergy.name,
                severity=link.severity,
            )
            for link in result["allergies"]
        ]

        restrictions_out = [
            DietaryRestrictionOut(
                id=link.id,
                restriction_id=link.restriction_id,
                restriction_name=link.restriction.name,
            )
            for link in result["dietary_restrictions"]
        ]

        return FullDietaryProfileOut(
            profile=profile_out,
            allergies=allergies_out,
            dietary_restrictions=restrictions_out,
        )