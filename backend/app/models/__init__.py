"""
=========================================================
AIMeals Backend
Models Package Init

Purpose:
    Imports every SQLAlchemy model class in one place, so
    the declarative mapper registry is fully populated
    BEFORE any query runs anywhere in the app.

Why this file exists:
    SQLAlchemy models that reference each other via a
    string-based relationship("SomeOtherModel") only work
    if SomeOtherModel has ALREADY been imported (i.e. its
    class has been defined) by the time SQLAlchemy needs to
    resolve that string — which happens the first time ANY
    query runs, not just queries touching that specific model.

    This project hit that repeatedly in isolated test/seed
    scripts (documented and worked around there with
    per-script "# noqa" imports). It was assumed NOT to
    affect the real running app, because main.py's import of
    the auth router happened to pull in enough models by
    coincidence.

    That assumption broke once AuthService started importing
    SubscriptionService (to fix the missing-default-subscription
    bug) — SubscriptionService imports InteractionType from
    ai_interaction.py, which defines AIInteraction with a
    relationship("Recipe"). Nothing in the real app's import
    chain had ever imported Recipe, so the very first user
    query (any query at all, e.g. a login) failed with:

        InvalidRequestError: ... expression 'Recipe' failed
        to locate a name ('Recipe') ...

    Rather than patch that one symptom, this file guarantees
    ALL models are imported together, permanently, so this
    class of bug can't resurface as more services get wired
    together through the rest of Phase 9 — regardless of
    which service happens to import which other service, or
    in what order.

    UPDATE (Aug 2026): this file itself was found to be
    incomplete — UsedEmail, MealConfirmationDismissal, and
    AllergenOverrideConsent existed as real tables (created
    via Base.metadata.create_all() at app startup, which
    picks up models from wherever main.py's import chain
    happens to reach) but were never added here. Since
    migrations/env.py imports this package specifically to
    populate target_metadata for Alembic's --autogenerate,
    those three tables were invisible to Alembic and it
    proposed DROPPING all three as part of an unrelated
    migration — caught before being applied, but a reminder
    that this file is the single source of truth and EVERY
    model must be added here the moment it's created, not
    just "wherever happens to import it first".

Usage:
    Imported once, early, in main.py:
        import app.models  # noqa
    Also imported by migrations/env.py, so --autogenerate
    can see every table.
    Must run before the app starts accepting requests.
=========================================================
"""

from app.models.ai_interaction import AIInteraction  # noqa: F401
from app.models.allergen_synonym import AllergenSynonym  # noqa: F401
from app.models.allergy import (  # noqa: F401
    Allergy,
    DietaryRestriction,
    UserAllergy,
    UserDietaryRestriction,
)
from app.models.food_image import FoodImage  # noqa: F401
from app.models.ingredient_scan import IngredientScan  # noqa: F401
from app.models.meal import Meal  # noqa: F401
from app.models.meal_plan import MealPlan  # noqa: F401
from app.models.nutrition_log import NutritionLog  # noqa: F401
from app.models.pantry_item import PantryItem  # noqa: F401
from app.models.profile import Profile  # noqa: F401
from app.models.progress_entry import ProgressEntry  # noqa: F401
from app.models.recipe import Recipe  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.daily_tip import DailyTip  # noqa: F401
from app.models.allergy_general_facts import AllergyGeneralFacts  # noqa: F401
from app.models.allergen_insight import AllergenInsight, UserAllergenDeepUnlock  # noqa: F401
from app.models.water_log import WaterLog  # noqa: F401
from app.models.food_image import FoodImage, FoodImageStatus  # noqa: F401
from app.models.report import Report, ReportComment, ReportCategory, ReportStatus  # noqa: F401
from app.models.meal_plan_chunk import MealPlanChunk, MealPlanChunkStatus  # noqa: F401
from app.models.email_verification import EmailVerification  # noqa: F401
from app.models.used_email import UsedEmail  # noqa: F401
from app.models.meal_confirmation_dismissal import MealConfirmationDismissal  # noqa: F401
from app.models.allergen_consent import AllergenOverrideConsent  # noqa: F401
from app.models.ad_reward_transaction import AdRewardTransaction  # noqa: F401
from app.models.revenuecat_webhook_event import RevenueCatWebhookEvent  # noqa: F401
from app.models.coach_memory import CoachMemoryFact  # noqa: F401
from app.models.achievement import AchievementDefinition, UserAchievement  # noqa: F401