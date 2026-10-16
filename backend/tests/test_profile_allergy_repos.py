from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.allergy_repository import (
    AllergyRepository,
    UserAllergyRepository,
)
from app.models.profile import Gender, ActivityLevel, Goal
from app.models.allergy import AllergySeverity
from datetime import date

db = SessionLocal()

# Get our existing test user
user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found — run the earlier repository test first")
else:
    # --- Profile ---
    profile_repo = ProfileRepository(db)

    profile = profile_repo.get_by_user_id(user.id)
    if profile is None:
        profile = profile_repo.create(
            user_id=user.id,
            date_of_birth=date(1995, 4, 12),
            gender=Gender.MALE,
            height_cm=175.0,
            weight_kg=75.0,
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            goal=Goal.WEIGHT_LOSS,
        )
        print("Created profile:", profile)
    else:
        print("Profile already exists:", profile)

    updated = profile_repo.update(profile, weight_kg=74.5)
    print("Updated profile weight:", updated.weight_kg)

    # --- Allergy lookup ---
    allergy_repo = AllergyRepository(db)

    peanuts = allergy_repo.get_by_name("Peanuts")
    if peanuts is None:
        peanuts = allergy_repo.create("Peanuts")
        print("Created allergy:", peanuts)
    else:
        print("Allergy already exists:", peanuts)

    # --- Link allergy to user ---
    user_allergy_repo = UserAllergyRepository(db)

    existing_links = user_allergy_repo.get_for_user(user.id)
    if any(link.allergy_id == peanuts.id for link in existing_links):
        print("User already linked to this allergy.")
    else:
        link = user_allergy_repo.add_to_user(user.id, peanuts.id, AllergySeverity.SEVERE)
        print("Linked allergy to user:", link)

    all_user_allergies = user_allergy_repo.get_for_user(user.id)
    print("User's allergies:", all_user_allergies)

db.close()