from app.B_database import init_database
from app.models.user import User  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.profile import Profile  # noqa: F401
from app.models.allergy import Allergy, DietaryRestriction, UserAllergy, UserDietaryRestriction  # noqa: F401
from app.models.recipe import Recipe  # noqa: F401
from app.models.nutrition_log import NutritionLog  # noqa: F401
from app.models.meal_plan import MealPlan  # noqa: F401
from app.models.meal import Meal  # noqa: F401
from app.models.pantry_item import PantryItem  # noqa: F401python -m tests.test_init_db
from app.models.pantry_item import PantryItem  # noqa: F401
from app.models.progress_entry import ProgressEntry  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401
init_database()