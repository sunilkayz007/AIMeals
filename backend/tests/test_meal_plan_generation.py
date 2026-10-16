from datetime import date, timedelta
from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.ai_service import AIService
from app.models.nutrition_log import MealType
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

    start = date.today()
    end = start + timedelta(days=1)

    try:
        plan = service.generate_meal_plan(
            user_id=user.id,
            title="Test 2-Day Pescatarian Plan",
            start_date=start,
            end_date=end,
            meal_types=[MealType.BREAKFAST, MealType.DINNER],
            preferences="High protein, pescatarian, easy to prepare.",
        )
        print("SUCCESS — Meal plan created:", plan.title)

        from app.repositories.meal_plan_repository import MealRepository
        meal_repo = MealRepository(db)
        meals = meal_repo.get_by_meal_plan(plan.id)
        print(f"\n{len(meals)} meals created:")
        for meal in meals:
            print(f"- {meal.scheduled_date} {meal.meal_type.value}: recipe_id={meal.recipe_id}")

        from app.repositories.recipe_repository import RecipeRepository
        recipe_repo = RecipeRepository(db)
        for meal in meals:
            if meal.recipe_id is None:
                print("\n  (meal has no linked recipe)")
                continue

            recipe = recipe_repo.get_by_id(meal.recipe_id)
            if recipe is None:
                print(f"\n  (recipe {meal.recipe_id} not found)")
                continue

            print(f"\n  Recipe: {recipe.title}")
            print(f"  Ingredients: {recipe.ingredients[:100]}...")

    except AllergenDetectedError as e:
        print("Rejected for allergen safety:", e)
    except (InsufficientCreditsError, ClaudeAPIError, RecipeGenerationError) as e:
        print("Other failure:", e)

db.close()