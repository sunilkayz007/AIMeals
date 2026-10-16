from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.ai_food_image import router as ai_food_image_router
from app.api.v1.reports import router as reports_router
# Import every model class BEFORE anything else runs, so
# SQLAlchemy's mapper registry is fully populated before the
# first query. See app/models/__init__.py for the full
# explanation of why this is necessary.
import app.models  # noqa: F401

from app.A_config import settings
from app.B_database import init_database
from app.C_logger import app_logger
from app.B_database import init_database, test_database_connection
from app.api.v1.ai_chat import router as ai_chat_router
from app.api.v1.ai_food_image import router as ai_food_image_router
from app.api.v1.ai_ingredient_scan import router as ai_ingredient_scan_router
from app.api.v1.ai_meal_estimate import router as ai_meal_estimate_router
from app.api.v1.ai_meal_plan import router as ai_meal_plan_router
from app.api.v1.ai_pantry import router as ai_pantry_router
from app.api.v1.ai_recipes import router as ai_recipe_router
from app.api.v1.auth import router as auth_router
from app.api.v1.meal_plans import router as meal_plan_router
from app.api.v1.nutrition_logs import router as nutrition_log_router
from app.api.v1.pantry import router as pantry_router
from app.api.v1.profile import router as profile_router
from app.api.v1.progress import router as progress_router
from app.api.v1.recipes import router as recipe_router
from app.api.v1.subscription import router as subscription_router
from app.api.v1.daily_tip import router as daily_tip_router
from app.api.v1.allergy_facts import router as allergy_facts_router
from app.api.v1.allergen_insight import router as allergen_insight_router
from app.api.v1.water_logs import router as water_log_router
from app.api.v1.health_reports import router as health_reports_router
from app.api.v1.ads import router as ads_router
from app.api.v1.revenuecat_webhook import router as revenuecat_webhook_router
from app.api.v1.coach_memory import router as coach_memory_router
from app.api.v1.achievements import router as achievements_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("Starting AIMeals Backend...")
    if test_database_connection():
        app_logger.info("PostgreSQL Connected Successfully")
    else:
        app_logger.error("Could not connect to PostgreSQL")

    init_database()
    yield
    app_logger.info("Stopping AIMeals Backend...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# DEV-ONLY CORS: allows any origin to call this API from a browser,
# needed so a locally-opened HTML file (origin "null") or a future
# React Native dev server can reach the API directly. TIGHTEN THIS
# before production — restrict allow_origins to the real frontend's
# actual domain(s) once deployed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(subscription_router)
app.include_router(pantry_router)
app.include_router(recipe_router)
app.include_router(nutrition_log_router)
app.include_router(meal_plan_router)
app.include_router(progress_router)
app.include_router(ai_chat_router)
app.include_router(ai_recipe_router)
app.include_router(ai_pantry_router)
app.include_router(ai_meal_plan_router)
app.include_router(ai_ingredient_scan_router)
app.include_router(ai_meal_estimate_router)
app.include_router(ai_food_image_router)
app.include_router(daily_tip_router)
app.include_router(allergy_facts_router)
app.include_router(allergen_insight_router)
app.include_router(water_log_router)
app.include_router(ai_food_image_router)
app.include_router(reports_router)
app.include_router(health_reports_router)
app.include_router(ads_router)
app.include_router(revenuecat_webhook_router)
app.include_router(coach_memory_router)
app.include_router(achievements_router)
@app.get("/")
async def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "Running",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "connected",
    }