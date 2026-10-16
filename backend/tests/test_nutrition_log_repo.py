from datetime import date, timedelta
from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.nutrition_log_repository import NutritionLogRepository
from app.models.nutrition_log import MealType
from app.models.recipe import Recipe  # noqa: F401 — must be imported for NutritionLog's relationship("Recipe") to resolve

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    log_repo = NutritionLogRepository(db)

    today = date.today()
    yesterday = today - timedelta(days=1)

    log1 = log_repo.create(
        user_id=user.id,
        logged_at=today,
        meal_type=MealType.LUNCH,
        food_name="Grilled Chicken Salad",
        calories=450,
        protein_g=35,
        carbs_g=20,
        fat_g=22,
    )
    print("Created log 1:", log1)

    log2 = log_repo.create(
        user_id=user.id,
        logged_at=yesterday,
        meal_type=MealType.DINNER,
        food_name="Pasta",
        calories=600,
        protein_g=20,
        carbs_g=80,
        fat_g=15,
    )
    print("Created log 2:", log2)

    todays_logs = log_repo.get_by_user_and_date(user.id, today)
    print("Today's logs:", todays_logs)

    all_logs = log_repo.get_by_user(user.id)
    print("All logs:", all_logs)

    ranged_logs = log_repo.get_by_user(user.id, start_date=today, end_date=today)
    print("Logs in range (today only):", ranged_logs)

    updated = log_repo.update(log1, calories=470)
    print("Updated log1 calories:", updated.calories)

db.close()