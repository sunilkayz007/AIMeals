from datetime import date, timedelta
from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.nutrition_log_service import NutritionLogService
from app.services.meal_plan_service import MealPlanService
from app.services.pantry_service import PantryService
from app.services.progress_service import ProgressService
from app.models.nutrition_log import MealType
from app.models.recipe import Recipe  # noqa: F401 — needed for various relationship("Recipe") resolutions
from app.core.exceptions import DuplicateProgressEntryError

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    # --- NutritionLogService ---
    print("=== NutritionLogService ===")
    log_service = NutritionLogService(db)

    manual_log = log_service.log_meal(
        user_id=user.id,
        logged_at=date.today(),
        meal_type=MealType.BREAKFAST,
        food_name="Oatmeal",
        calories=300,
        protein_g=10,
        carbs_g=50,
        fat_g=5,
    )
    print("Manual log created:", manual_log)

    totals = log_service.get_daily_totals(user.id, date.today())
    print("Daily totals:", totals)

    # --- MealPlanService ---
    print("\n=== MealPlanService ===")
    plan_service = MealPlanService(db)

    plan = plan_service.create_plan(
        user_id=user.id,
        title="Service Layer Test Plan",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=6),
    )
    print("Plan created:", plan)

    meal = plan_service.add_meal(plan.id, user.id, date.today(), MealType.LUNCH)
    print("Meal added:", meal)

    week_meals = plan_service.get_meals_for_week(user.id, date.today(), date.today() + timedelta(days=6))
    print("This week's meals (cross-plan query):", week_meals)

    # --- PantryService ---
    print("\n=== PantryService ===")
    pantry_service = PantryService(db)

    item = pantry_service.add_item(
        user_id=user.id,
        ingredient_name="Spinach",
        quantity=1,
        unit="bag",
        expiration_date=date.today() + timedelta(days=2),
    )
    print("Pantry item added:", item)

    expiring = pantry_service.get_expiring_soon(user.id, within_days=3)
    print("Expiring soon:", expiring)

    # --- ProgressService ---
    print("\n=== ProgressService ===")
    progress_service = ProgressService(db)

    existing_today = progress_service.get_entry_for_date(user.id, date.today())
    if existing_today is None:
        entry = progress_service.log_entry(user.id, date.today(), weight_kg=74.0)
        print("Progress entry created:", entry)
    else:
        print("Progress entry already exists for today:", existing_today)

    # Try to create a duplicate for today — should be blocked
    try:
        progress_service.log_entry(user.id, date.today(), weight_kg=99.0)
        print("ERROR: duplicate progress entry was incorrectly allowed")
    except DuplicateProgressEntryError as e:
        print("Correctly blocked duplicate progress entry:", e)

db.close()