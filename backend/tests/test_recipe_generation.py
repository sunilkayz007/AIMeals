from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.ai_service import AIService
from app.core.exceptions import (
    InsufficientCreditsError,
    ClaudeAPIError,
    RecipeGenerationError,
    AllergenDetectedError,
)

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    service = AIService(db)

    print("=== Test 1: Normal request (should succeed) ===")
    try:
        recipe = service.generate_recipe(
            user_id=user.id,
            request_description="A quick high-protein lunch, ready in under 20 minutes.",
        )
        print("SUCCESS — Recipe generated:", recipe.title)
        print("Ingredients:\n", recipe.ingredients)
    except AllergenDetectedError as e:
        print("Rejected for allergen (unexpected here):", e)
    except (InsufficientCreditsError, ClaudeAPIError, RecipeGenerationError) as e:
        print("Other failure:", e)

    print("\n=== Test 2: Deliberately requesting the user's known allergen ===")
    try:
        recipe = service.generate_recipe(
            user_id=user.id,
            request_description="A peanut satay stir fry with peanut sauce.",
        )
        print("SUCCESS (this would be BAD — allergen check should have caught this):", recipe.title)
    except AllergenDetectedError as e:
        print("Correctly rejected — allergen safety check worked:", e)
    except (InsufficientCreditsError, ClaudeAPIError, RecipeGenerationError) as e:
        print("Other failure:", e)

db.close()