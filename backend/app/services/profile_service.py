"""
=========================================================
AIMeals Backend
Profile Service

Responsibilities:
    - Orchestrate profile creation/update
    - Manage a user's linked allergies and dietary restrictions
    - Compute personalized RDA-based nutrient targets
    - Contains the business logic for this domain — framework
      agnostic, raises custom exceptions, no HTTP concepts

Dependencies:
    - app.repositories.profile_repository.ProfileRepository
    - app.repositories.allergy_repository (all four repos)
    - app.core.rda.compute_rda_targets
    - app.core.exceptions

Example usage:
    from app.services.profile_service import ProfileService

    service = ProfileService(db)
    service.create_or_update_profile(user.id, weight_kg=74.5)
    service.add_allergy(user.id, "Peanuts", AllergySeverity.SEVERE)
=========================================================
"""

import uuid
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateAllergyError, DuplicateRestrictionError
from app.core.rda import NutrientTarget, compute_rda_targets
from app.models.allergy import AllergySeverity
from app.models.profile import ActivityLevel, Gender, Goal, Profile
from app.repositories.allergy_repository import (
    AllergyRepository,
    DietaryRestrictionRepository,
    UserAllergyRepository,
    UserDietaryRestrictionRepository,
)
from app.core.geolocation import get_country_code_from_ip
from app.repositories.profile_repository import ProfileRepository


# One-line disclaimer shown by the client alongside every RDA-based
# target — see app.core.rda's module docstring for the full reasoning
# on why these are general population averages, not personalized
# medical guidance.
RDA_DISCLAIMER = (
    "Estimated using standard RDA guidelines based on your age, "
    "gender, and weight — not personalized medical advice."
)


# =========================================================
# Profile Service
# =========================================================

class ProfileService:
    """
    Contains the business logic for profile, allergy, and
    dietary restriction management.
    """

    def __init__(self, db: Session):
        self.db = db
        self.profile_repo = ProfileRepository(db)
        self.allergy_repo = AllergyRepository(db)
        self.restriction_repo = DietaryRestrictionRepository(db)
        self.user_allergy_repo = UserAllergyRepository(db)
        self.user_restriction_repo = UserDietaryRestrictionRepository(db)

    # ---------------------------------------------------
    # Profile
    # ---------------------------------------------------

    def get_profile(self, user_id: uuid.UUID) -> Optional[Profile]:
        """
        Returns the user's profile, or None if they haven't
        created one yet. Not having a profile is a normal
        state, not an error — most callers should handle
        None gracefully (e.g. show a "complete your profile"
        prompt) rather than treating it as exceptional.
        """
        return self.profile_repo.get_by_user_id(user_id)

    def create_or_update_profile(
        self,
        user_id: uuid.UUID,
        date_of_birth: Optional[date] = None,
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
        Creates a profile if the user doesn't have one yet,
        or updates the existing one. Callers don't need to
        know or care which case applies — this method
        handles both, so a profile-edit screen can always
        call this same method regardless of whether it's
        the user's first save or their hundredth.

        Only fields explicitly passed (non-None) are applied
        on update, so partial edits don't wipe out other
        fields.
        """
        existing = self.profile_repo.get_by_user_id(user_id)

        if existing is None:
            return self.profile_repo.create(
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

        fields_to_update = {
            key: value
            for key, value in {
                "date_of_birth": date_of_birth,
                "gender": gender,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "activity_level": activity_level,
                "goal": goal,
                "daily_calorie_target": daily_calorie_target,
                "protein_g_target": protein_g_target,
                "carbs_g_target": carbs_g_target,
                "fat_g_target": fat_g_target,
                "fiber_g_target": fiber_g_target,
                "daily_water_ml_target": daily_water_ml_target,
                "typical_wake_time": typical_wake_time,
                "region_code": region_code,
            }.items()
            if value is not None
        }

        return self.profile_repo.update(existing, **fields_to_update)

    # ---------------------------------------------------
    # IP-Based Region Detection
    # ---------------------------------------------------

    def detect_and_save_region(
        self,
        user_id: uuid.UUID,
        client_ip: str,
    ) -> Optional[str]:
        """
        Resolves client_ip to a country code (see
        app.core.geolocation.get_country_code_from_ip -- returns
        None for local/private IPs, unreachable service, or any
        other failure) and saves it to the user's profile if it's
        actually different from what's already stored, creating
        the profile first if the user has none yet.

        REPLACES the earlier device-locale-based signal, which
        conflated language preference with physical location (a
        user can set their phone to "English (United States)"
        while living anywhere else) -- see
        app.core.geolocation's own module docstring for the full
        reasoning, including why this returns None entirely when
        called against a local/dev backend (no public IP to
        resolve).

        Returns the resolved country code (which may be the same
        as what was already stored, or None if nothing could be
        resolved) -- purely informational for the caller; this
        method's side effect (saving it) is the real point, not
        its return value.
        """
        country_code = get_country_code_from_ip(client_ip)

        if country_code is None:
            return None

        existing = self.profile_repo.get_by_user_id(user_id)

        if existing is not None and existing.region_code == country_code:
            # Already up to date -- skip the write entirely.
            return country_code

        self.create_or_update_profile(user_id=user_id, region_code=country_code)
        return country_code

    # ---------------------------------------------------
    # RDA-Based Nutrient Targets
    # ---------------------------------------------------

    def get_rda_targets(self, user_id: uuid.UUID) -> dict:
        """
        Computes the 10 auto-personalized mineral/vitamin
        targets (see app.core.rda) from the user's stored
        age (derived from date_of_birth), gender, and weight.

        Returns a dict of {nutrient_key: NutrientTarget, ...,
        "disclaimer": RDA_DISCLAIMER} — the controller wraps
        this directly into RDATargetsOut.

        Raises:
            ValueError: no profile exists yet for
                this user, OR the existing profile is missing
                date_of_birth (age cannot be computed without
                it). Either way, the caller (route/controller)
                should surface this as "complete your body
                details first" rather than a generic 500 —
                this is a normal, expected state for a new
                user, not a system failure.
        """
        profile = self.profile_repo.get_by_user_id(user_id)

        if profile is None or profile.date_of_birth is None:
            # Plain ValueError, not a custom exceptions-module class —
            # this method's only caller (the controller) catches
            # ValueError directly and maps it to a 400, so no new
            # exception type needs to be added to app.core.exceptions
            # just for this one case.
            raise ValueError(
                "Age is required to compute nutrient targets — "
                "please add your date of birth in Body Details first."
            )

        today = date.today()
        age = today.year - profile.date_of_birth.year - (
            (today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day)
        )

        gender_value = profile.gender.value if profile.gender is not None else None

        targets: dict[str, NutrientTarget] = compute_rda_targets(
            age=age,
            gender=gender_value,
            weight_kg=profile.weight_kg,
        )

        result: dict = {key: target for key, target in targets.items()}
        result["disclaimer"] = RDA_DISCLAIMER
        return result

    # ---------------------------------------------------
    # Allergies
    # ---------------------------------------------------

    def add_allergy(
        self,
        user_id: uuid.UUID,
        allergy_name: str,
        severity: AllergySeverity = AllergySeverity.MODERATE,
    ) -> None:
        """
        Links an allergy to a user, creating the allergy in
        the master lookup list first if it doesn't exist yet.

        Raises:
            DuplicateAllergyError: if the user already has
                this allergy linked.
        """
        allergy = self.allergy_repo.get_by_name(allergy_name)
        if allergy is None:
            allergy = self.allergy_repo.create(allergy_name)

        existing_links = self.user_allergy_repo.get_for_user(user_id)
        if any(link.allergy_id == allergy.id for link in existing_links):
            raise DuplicateAllergyError(
                f"User already has an allergy entry for '{allergy_name}'."
            )

        self.user_allergy_repo.add_to_user(user_id, allergy.id, severity)

    def remove_allergy(self, user_id: uuid.UUID, allergy_id: uuid.UUID) -> None:
        """
        Removes an allergy link from a user. Silently does
        nothing if the link doesn't exist — removal should
        be idempotent.
        """
        existing_links = self.user_allergy_repo.get_for_user(user_id)
        match = next((link for link in existing_links if link.allergy_id == allergy_id), None)

        if match is not None:
            self.user_allergy_repo.remove_from_user(match)

    # ---------------------------------------------------
    # Dietary Restrictions
    # ---------------------------------------------------

    def add_dietary_restriction(self, user_id: uuid.UUID, restriction_name: str) -> None:
        """
        Links a dietary restriction to a user, creating it in
        the master lookup list first if it doesn't exist yet.

        Raises:
            DuplicateRestrictionError: if the user already
                has this restriction linked.
        """
        restriction = self.restriction_repo.get_by_name(restriction_name)
        if restriction is None:
            restriction = self.restriction_repo.create(restriction_name)

        existing_links = self.user_restriction_repo.get_for_user(user_id)
        if any(link.restriction_id == restriction.id for link in existing_links):
            raise DuplicateRestrictionError(
                f"User already has a dietary restriction entry for '{restriction_name}'."
            )

        self.user_restriction_repo.add_to_user(user_id, restriction.id)

    def remove_dietary_restriction(self, user_id: uuid.UUID, restriction_id: uuid.UUID) -> None:
        """
        Removes a dietary restriction link from a user.
        Silently does nothing if the link doesn't exist.
        """
        existing_links = self.user_restriction_repo.get_for_user(user_id)
        match = next(
            (link for link in existing_links if link.restriction_id == restriction_id),
            None,
        )

        if match is not None:
            self.user_restriction_repo.remove_from_user(match)

    # ---------------------------------------------------
    # Combined View
    # ---------------------------------------------------

    def get_full_dietary_profile(self, user_id: uuid.UUID) -> dict:
        """
        Returns the profile, allergies, and dietary
        restrictions together. AI features (recipe
        generation, meal planning) almost always need all
        three at once, so this saves every caller from
        re-assembling this combination themselves.
        """
        return {
            "profile": self.get_profile(user_id),
            "allergies": self.user_allergy_repo.get_for_user(user_id),
            "dietary_restrictions": self.user_restriction_repo.get_for_user(user_id),
        }