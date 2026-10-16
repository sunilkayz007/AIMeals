"""
=========================================================
AIMeals Backend
Profile API Routes

Endpoints:
    GET    /api/v1/profile                              - get the current user's profile (null if not created yet)
    PUT    /api/v1/profile                               - create or update the current user's profile
    GET    /api/v1/profile/full                          - profile + allergies + dietary restrictions combined
    GET    /api/v1/profile/rda-targets                    - auto-computed vitamin/mineral targets (age/gender/weight-based)
    POST   /api/v1/profile/detect-region                  - resolve caller's IP to a country code and save it (silent, best-effort)
    POST   /api/v1/profile/allergies                     - link an allergy to the current user
    DELETE /api/v1/profile/allergies/{allergy_id}         - unlink an allergy (idempotent)
    POST   /api/v1/profile/dietary-restrictions           - link a dietary restriction
    DELETE /api/v1/profile/dietary-restrictions/{restriction_id} - unlink a dietary restriction (idempotent)

All endpoints require a valid access token (Authorization: Bearer <token>).

Dependencies:
    - app.controller.profile_controller.ProfileController
    - app.core.dependencies.get_current_user
    - app.B_database.get_db
=========================================================
"""

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.controller.profile_controller import ProfileController
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.profile import (
    AllergyCreate,
    DietaryRestrictionCreate,
    FullDietaryProfileOut,
    ProfileOut,
    ProfileUpdate,
    RDATargetsOut,
)

router = APIRouter(prefix="/api/v1/profile", tags=["Profile"])


# =========================================================
# Get Profile
# =========================================================

@router.get(
    "",
    response_model=ProfileOut | None,
    status_code=status.HTTP_200_OK,
)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut | None:
    """
    Returns the current user's profile, or null if they
    haven't created one yet (a normal state, not an error).
    """
    controller = ProfileController(db)
    return controller.get_profile(current_user.id)


# =========================================================
# Create/Update Profile
# =========================================================

@router.put(
    "",
    response_model=ProfileOut,
    status_code=status.HTTP_200_OK,
)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut:
    """
    Creates the profile if it doesn't exist yet, or applies a
    partial update if it does. Only fields explicitly included
    in the request body are changed.
    """
    controller = ProfileController(db)
    return controller.update_profile(current_user.id, payload)


# =========================================================
# Combined Dietary Profile View
# =========================================================

@router.get(
    "/full",
    response_model=FullDietaryProfileOut,
    status_code=status.HTTP_200_OK,
)
def get_full_dietary_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FullDietaryProfileOut:
    """
    Returns profile, allergies, and dietary restrictions
    together — the shape AI features (recipe generation,
    meal planning) typically need in one call.
    """
    controller = ProfileController(db)
    return controller.get_full_dietary_profile(current_user.id)


# =========================================================
# RDA-Based Nutrient Targets
# =========================================================

@router.get(
    "/rda-targets",
    response_model=RDATargetsOut,
    status_code=status.HTTP_200_OK,
)
def get_rda_targets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RDATargetsOut:
    """
    Returns 10 auto-computed mineral/vitamin daily targets
    (Sodium, Potassium, Calcium, Iron, Magnesium, Zinc,
    Vitamin A, B12, C, D), personalized from the user's
    stored age, gender, and weight.

    Returns 400 if the user has no profile yet, or their
    profile has no date_of_birth set — age is required to
    compute these targets.
    """
    controller = ProfileController(db)
    return controller.get_rda_targets(current_user.id)


# =========================================================
# Detect Region (IP-based, silent, best-effort)
# =========================================================

@router.post(
    "/detect-region",
    status_code=status.HTTP_200_OK,
)
def detect_region(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Resolves the caller's IP address to a country code and saves
    it to their profile if it's different from what's already
    stored -- replaces the earlier device-locale-based signal,
    which conflated language preference with physical location.
    See app.core.geolocation's module docstring for the full
    reasoning, including why this always returns null when called
    against a local/dev backend (no public IP to resolve there).

    The client is expected to call this once, silently, on app
    launch (e.g. from Home's mount effect) and ignore the
    response -- this is a background sync, not a user-facing
    action. Never fails loudly: an unresolvable IP or unreachable
    geolocation service just returns {"region_code": null}, not
    an error.

    IP extraction checks X-Forwarded-For first (set by the Nginx
    reverse proxy in front of this app in production -- see
    deployment notes), falling back to the raw connection IP
    (request.client.host) for local development without a proxy
    in front. X-Forwarded-For can contain a comma-separated chain
    of proxies; the FIRST entry is the original client.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host
    else:
        client_ip = ""

    controller = ProfileController(db)
    region_code = controller.detect_region(current_user.id, client_ip)

    return {"region_code": region_code}


# =========================================================
# Add Allergy
# =========================================================

@router.post(
    "/allergies",
    status_code=status.HTTP_204_NO_CONTENT,
)
def add_allergy(
    payload: AllergyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Links an allergy to the current user. Creates the allergy
    in the master lookup list first if it doesn't exist yet.

    Returns 409 if the user already has this allergy linked.
    """
    controller = ProfileController(db)
    controller.add_allergy(current_user.id, payload)


# =========================================================
# Remove Allergy
# =========================================================

@router.delete(
    "/allergies/{allergy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_allergy(
    allergy_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Unlinks an allergy from the current user. Idempotent —
    no error if the link doesn't exist.
    """
    controller = ProfileController(db)
    controller.remove_allergy(current_user.id, allergy_id)


# =========================================================
# Add Dietary Restriction
# =========================================================

@router.post(
    "/dietary-restrictions",
    status_code=status.HTTP_204_NO_CONTENT,
)
def add_dietary_restriction(
    payload: DietaryRestrictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Links a dietary restriction to the current user. Creates
    it in the master lookup list first if it doesn't exist yet.

    Returns 409 if the user already has this restriction linked.
    """
    controller = ProfileController(db)
    controller.add_dietary_restriction(current_user.id, payload)


# =========================================================
# Remove Dietary Restriction
# =========================================================

@router.delete(
    "/dietary-restrictions/{restriction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_dietary_restriction(
    restriction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Unlinks a dietary restriction from the current user.
    Idempotent — no error if the link doesn't exist.
    """
    controller = ProfileController(db)
    controller.remove_dietary_restriction(current_user.id, restriction_id)