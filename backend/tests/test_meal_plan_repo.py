from datetime import date, timedelta
from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.meal_plan_repository import MealPlanRepository, MealRepository
from app.models.nutrition_log import MealType
from app.models.recipe import Recipe  # noqa: F401 — needed for Meal's relationship("Recipe")

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    plan_repo = MealPlanRepository(db)
    meal_repo = MealRepository(db)

    today = date.today()
    week_end = today + timedelta(days=6)

    plan = plan_repo.create(
        user_id=user.id,
        title="Test Week Plan",
        start_date=today,
        end_date=week_end,
    )
    print("Created meal plan:", plan)

    meal1 = meal_repo.create(
        meal_plan_id=plan.id,
        scheduled_date=today,
        meal_type=MealType.DINNER,
    )
    print("Created meal 1:", meal1)

    meal2 = meal_repo.create(
        meal_plan_id=plan.id,
        scheduled_date=today + timedelta(days=1),
        meal_type=MealType.LUNCH,
    )
    print("Created meal 2:", meal2)

    plan_meals = meal_repo.get_by_meal_plan(plan.id)
    print("Meals in plan:", plan_meals)

    ranged_meals = meal_repo.get_by_user_and_date_range(user.id, today, week_end)
    print("User's meals this week (via join):", ranged_meals)

    # Delete the plan — should cascade-delete both meals
    plan_id = plan.id
    plan_repo.delete(plan)

    remaining = meal_repo.get_by_meal_plan(plan_id)
    print("Meals remaining after plan deletion (should be empty):", remaining)

db.close()