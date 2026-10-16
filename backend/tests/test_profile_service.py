from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.profile_service import ProfileService
from app.models.profile import Goal
from app.models.allergy import AllergySeverity
from app.core.exceptions import DuplicateAllergyError

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    service = ProfileService(db)

    # create_or_update_profile — should update existing profile from earlier tests
    profile = service.create_or_update_profile(user.id, goal=Goal.MUSCLE_GAIN)
    print("Profile after update:", profile)

    # Partial update shouldn't wipe other fields
    print("Height still set:", profile.height_cm)

    # Try adding an allergy that likely already exists from earlier tests
    try:
        service.add_allergy(user.id, "Peanuts", AllergySeverity.SEVERE)
        print("Added Peanuts allergy (unexpected — should have already existed)")
    except DuplicateAllergyError as e:
        print("Correctly rejected duplicate allergy:", e)

    # Add a genuinely new allergy
    try:
        service.add_allergy(user.id, "Shellfish", AllergySeverity.MILD)
        print("Added Shellfish allergy successfully")
    except DuplicateAllergyError as e:
        print("Unexpected duplicate error:", e)

    # Add a dietary restriction
    service.add_dietary_restriction(user.id, "Pescatarian")
    print("Added Pescatarian restriction")

    # Full combined view
    full_profile = service.get_full_dietary_profile(user.id)
    print("\nFull dietary profile:")
    print("Profile:", full_profile["profile"])
    print("Allergies:", full_profile["allergies"])
    print("Restrictions:", full_profile["dietary_restrictions"])

db.close()