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

    print("=== Test: Auto-select from pantry (no explicit selection) ===")
    try:
        recipe = service.suggest_recipe_from_pantry(
            user_id=user.id,
            additional_preferences="Keep it simple and quick.",
        )
        print("SUCCESS — Recipe generated:", recipe.title)
        print("Ingredients:\n", recipe.ingredients)

        # Confirm it's logged under PANTRY_SUGGESTION, not RECIPE_GENERATION
        from app.repositories.ai_interaction_repository import AIInteractionRepository
        interaction_repo = AIInteractionRepository(db)
        recent = interaction_repo.get_by_user(user.id, limit=1)
        print("\nLogged interaction type:", recent[0].interaction_type)

    except AllergenDetectedError as e:
        print("Rejected for allergen safety:", e)
    except RecipeGenerationError as e:
        print("Recipe generation failed:", e)
    except (InsufficientCreditsError, ClaudeAPIError) as e:
        print("Other failure:", e)

db.close()