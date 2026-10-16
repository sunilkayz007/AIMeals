"""
=========================================================
AIMeals Backend
Nutrition Log Service

Responsibilities:
    - Orchestrate meal logging: manual, recipe-based, and
      food-image-scan-based
    - Compute daily nutrition totals
    - Power the "did you eat this?" soft-prompt feature:
      selecting which recent recipes/scans to ask about, and
      recording dismissals
    - Enforce ownership on edits/deletes

Dependencies:
    - app.repositories.nutrition_log_repository.NutritionLogRepository
    - app.repositories.recipe_repository.RecipeRepository
    - app.repositories.food_image_repository.FoodImageRepository
    - app.repositories.meal_confirmation_dismissal_repository.MealConfirmationDismissalRepository
    - app.core.exceptions

Example usage:
    from app.services.nutrition_log_service import NutritionLogService

    service = NutritionLogService(db)
    service.log_meal_from_recipe(user.id, date.today(), MealType.DINNER, recipe.id)
    totals = service.get_daily_totals(user.id, date.today())
=========================================================
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import (
    FoodImageNotConfirmedError,
    FoodImageNotFoundError,
    NotFoodImageOwnerError,
    NotLogOwnerError,
    NutritionLogNotFoundError,
    RecipeNotFoundError,
)
from app.models.food_image import FoodImageStatus
from app.models.nutrition_log import MealType, NutritionLog
from app.repositories.food_image_repository import FoodImageRepository
from app.repositories.meal_confirmation_dismissal_repository import (
    MealConfirmationDismissalRepository,
)
from app.repositories.nutrition_log_repository import NutritionLogRepository
from app.repositories.recipe_repository import RecipeRepository
from app.core.micronutrients import scale_micronutrients, sum_micronutrients
from app.services.achievement_service import AchievementService
from app.C_logger import app_logger

# How far back to look for recipes/scans worth asking "did you eat
# this?" about. Anything older is just quietly dropped rather than
# nagging about something from days ago.
PENDING_CONFIRMATION_WINDOW_HOURS = 48


# =========================================================
# Nutrition Log Service
# =========================================================

class NutritionLogService:
    """
    Contains the business logic for meal logging.
    """

    def __init__(self, db: Session):
        self.db = db
        self.log_repo = NutritionLogRepository(db)
        self.recipe_repo = RecipeRepository(db)
        self.food_image_repo = FoodImageRepository(db)
        self.dismissal_repo = MealConfirmationDismissalRepository(db)
        self.achievement_service = AchievementService(db)

    # ---------------------------------------------------
    # Achievements — Best-Effort Streak Check
    # ---------------------------------------------------

    def _check_achievements_best_effort(self, user_id: uuid.UUID) -> None:
        """
        Called after every successful meal-log creation (all 3
        log_meal* methods below) to check/award logging-streak
        achievements. Deliberately best-effort: any failure here
        is logged and swallowed, never re-raised — an achievement-
        checking bug must never turn into a failed meal log for
        the user, since logging the meal is the actual point of
        the request.
        """
        try:
            self.achievement_service.check_and_award_streaks(user_id)
        except Exception:
            app_logger.exception(
                f"Achievement streak check failed for user {user_id} after a "
                f"meal log — the log itself was saved successfully and is "
                f"unaffected."
            )

    # ---------------------------------------------------
    # Create — Manual Entry
    # ---------------------------------------------------

    def log_meal(
        self,
        user_id: uuid.UUID,
        logged_at: date,
        meal_type: MealType,
        food_name: str,
        calories: float,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
        fiber_g: float = 0.0,
        water_ml: float = 0.0,
        micronutrients: Optional[dict] = None,
        recipe_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> NutritionLog:
        """
        Logs a meal with manually-provided nutrition values.
        recipe_id is optional here too (a manual entry can
        still reference a recipe for record-keeping, without
        pulling its macros automatically) — use
        log_meal_from_recipe() instead when you want the
        macros auto-filled.

        fiber_g and water_ml both default to 0.0 — a manual
        entry has no recipe/scan to estimate them from, so
        unless the caller explicitly provides a value, this
        entry simply doesn't contribute to the day's fiber/
        water totals. micronutrients defaults to None (no
        data) rather than a dict of zeros — see
        app.core.micronutrients for how a None/missing dict
        is treated as all-zeros only when READ (get_daily_totals),
        not fabricated at write time.
        """
        new_log = self.log_repo.create(
            user_id=user_id,
            logged_at=logged_at,
            meal_type=meal_type,
            food_name=food_name,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            fiber_g=fiber_g,
            water_ml=water_ml,
            micronutrients=micronutrients,
            recipe_id=recipe_id,
            notes=notes,
        )
        self._check_achievements_best_effort(user_id)
        return new_log

    # ---------------------------------------------------
    # Create — From Recipe (auto-filled macros)
    # ---------------------------------------------------

    def log_meal_from_recipe(
        self,
        user_id: uuid.UUID,
        logged_at: date,
        meal_type: MealType,
        recipe_id: uuid.UUID,
        portion_percentage: float = 100.0,
        notes: Optional[str] = None,
    ) -> NutritionLog:
        """
        Logs a meal using a recipe's stored nutrition values,
        scaled by portion_percentage — so the user doesn't have
        to re-type macros that already exist on the recipe, and
        can log a partial portion (e.g. "I had 60% of this").

        Raises:
            RecipeNotFoundError: if no recipe exists with
                this id.

        Note: a recipe's nutrition fields are all Optional
        (see Recipe model), so if the recipe itself has no
        calorie/macro/fiber data recorded, the log entry will
        inherit those same None-equivalent (0) gaps, scaled
        the same as everything else. This method doesn't
        fabricate numbers the recipe doesn't have.
        """
        recipe = self.recipe_repo.get_by_id(recipe_id)

        if recipe is None:
            raise RecipeNotFoundError(f"No recipe found with id {recipe_id}.")

        scale = portion_percentage / 100.0

        new_log = self.log_repo.create(
            user_id=user_id,
            logged_at=logged_at,
            meal_type=meal_type,
            food_name=recipe.title,
            calories=(recipe.calories_per_serving or 0) * scale,
            protein_g=(recipe.protein_g or 0) * scale,
            carbs_g=(recipe.carbs_g or 0) * scale,
            fat_g=(recipe.fat_g or 0) * scale,
            fiber_g=(recipe.fiber_g_per_serving or 0) * scale,
            water_ml=(recipe.water_ml_per_serving or 0) * scale,
            micronutrients=scale_micronutrients(recipe.micronutrients, scale),
            recipe_id=recipe.id,
            portion_percentage=portion_percentage,
            notes=notes,
        )
        self._check_achievements_best_effort(user_id)
        return new_log

    # ---------------------------------------------------
    # Create — From Food Image Scan (auto-filled macros)
    # ---------------------------------------------------

    def log_meal_from_food_image(
        self,
        user_id: uuid.UUID,
        logged_at: date,
        meal_type: MealType,
        food_image_id: uuid.UUID,
        portion_percentage: float = 100.0,
        notes: Optional[str] = None,
    ) -> NutritionLog:
        """
        Logs a meal using a food-image scan's computed totals,
        scaled by portion_percentage — same reasoning as
        log_meal_from_recipe(), for scans instead of recipes.

        The scan must be CONFIRMED, not PENDING — an unresolved
        ambiguous item means the totals aren't final yet. The
        caller should have the user resolve it first via the
        existing free POST /food-images/{id}/resolve endpoint.

        food_name is built from the scan's detected item names
        (up to 3, with a "+N more" suffix if there are more),
        since a FoodImage has no single title the way a Recipe
        does.

        Raises:
            FoodImageNotFoundError: no such scan exists.
            NotFoodImageOwnerError: it belongs to another user.
            FoodImageNotConfirmedError: the scan is still
                PENDING (unresolved ambiguity).
        """
        food_image = self.food_image_repo.get_by_id(food_image_id)

        if food_image is None:
            raise FoodImageNotFoundError(f"No food image found with id {food_image_id}.")

        if food_image.user_id != user_id:
            raise NotFoodImageOwnerError("This food image belongs to another user.")

        if food_image.status != FoodImageStatus.CONFIRMED:
            raise FoodImageNotConfirmedError(
                "This scan still has unresolved items — resolve the ambiguity "
                "before logging it."
            )

        scale = portion_percentage / 100.0

        food_names = [item.get("name", "?") for item in (food_image.detected_foods or [])]
        if len(food_names) <= 3:
            food_name = ", ".join(food_names) if food_names else "Scanned meal"
        else:
            food_name = f"{', '.join(food_names[:3])} +{len(food_names) - 3} more"

        new_log = self.log_repo.create(
            user_id=user_id,
            logged_at=logged_at,
            meal_type=meal_type,
            food_name=food_name,
            calories=(food_image.total_calories or 0) * scale,
            protein_g=(food_image.total_protein_g or 0) * scale,
            carbs_g=(food_image.total_carbs_g or 0) * scale,
            fat_g=(food_image.total_fat_g or 0) * scale,
            fiber_g=(food_image.total_fiber_g or 0) * scale,
            water_ml=(food_image.total_water_ml or 0) * scale,
            micronutrients=scale_micronutrients(food_image.total_micronutrients, scale),
            food_image_id=food_image.id,
            portion_percentage=portion_percentage,
            notes=notes,
        )
        self._check_achievements_best_effort(user_id)
        return new_log

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_logs_for_day(self, user_id: uuid.UUID, target_date: date) -> List[NutritionLog]:
        return self.log_repo.get_by_user_and_date(user_id, target_date)

    def get_logs_for_range(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> List[NutritionLog]:
        return self.log_repo.get_by_user(user_id, start_date=start_date, end_date=end_date)

    def get_daily_totals(self, user_id: uuid.UUID, target_date: date) -> dict:
        """
        Returns summed calories/protein/carbs/fat/fiber/water
        across all of a user's log entries for a single day.
        Returns zeros (not None/missing keys) if the user has
        no entries that day, so callers can always safely use
        the result in arithmetic or display it directly.
        """
        logs = self.log_repo.get_by_user_and_date(user_id, target_date)

        return {
            "calories": sum(log.calories for log in logs),
            "protein_g": sum(log.protein_g for log in logs),
            "carbs_g": sum(log.carbs_g for log in logs),
            "fat_g": sum(log.fat_g for log in logs),
            "fiber_g": sum(log.fiber_g for log in logs),
            "water_ml": sum(log.water_ml for log in logs),
            # Sums all 10 tracked micronutrients across today's logs
            # into one dict — see app.core.micronutrients for why a
            # log with no micronutrient data (None) contributes zeros
            # rather than being skipped or raising.
            "micronutrients": sum_micronutrients(log.micronutrients for log in logs),
            "entry_count": len(logs),
        }

    # ---------------------------------------------------
    # Pending Meal Confirmations ("did you eat this?")
    # ---------------------------------------------------

    def get_pending_confirmations(self, user_id: uuid.UUID) -> List[dict]:
        """
        Returns recipes and confirmed food-image scans from the
        last PENDING_CONFIRMATION_WINDOW_HOURS hours that:
          - belong to this user (recipe_repo.get_by_user /
            food_image_repo.get_by_user already scope to the
            user — system/curated recipes are never included,
            since they aren't something "you just made")
          - have NO nutrition_log entry yet (checked against
            log_repo.get_logged_recipe_ids/get_logged_food_image_ids)
          - have NOT been explicitly dismissed
            (dismissal_repo.get_dismissed_recipe_ids/
            get_dismissed_food_image_ids)
          - for food images specifically: status must be
            CONFIRMED, not PENDING — an unresolved scan isn't
            ready to be asked about yet

        Returns a list of dicts shaped like PendingConfirmationOut
        (source_type, source_id, title, macros, created_at),
        sorted most-recent-first. The controller converts these
        into the actual response schema.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=PENDING_CONFIRMATION_WINDOW_HOURS)

        logged_recipe_ids = self.log_repo.get_logged_recipe_ids(user_id)
        logged_food_image_ids = self.log_repo.get_logged_food_image_ids(user_id)
        dismissed_recipe_ids = self.dismissal_repo.get_dismissed_recipe_ids(user_id)
        dismissed_food_image_ids = self.dismissal_repo.get_dismissed_food_image_ids(user_id)

        results: List[dict] = []

        for recipe in self.recipe_repo.get_by_user(user_id):
            if recipe.created_at < cutoff:
                continue
            if recipe.id in logged_recipe_ids or recipe.id in dismissed_recipe_ids:
                continue
            results.append({
                "source_type": "recipe",
                "source_id": recipe.id,
                "title": recipe.title,
                "calories": recipe.calories_per_serving,
                "protein_g": recipe.protein_g,
                "carbs_g": recipe.carbs_g,
                "fat_g": recipe.fat_g,
                "created_at": recipe.created_at,
            })

        for food_image in self.food_image_repo.get_by_user(user_id):
            if food_image.status != FoodImageStatus.CONFIRMED:
                continue
            if food_image.uploaded_at < cutoff:
                continue
            if food_image.id in logged_food_image_ids or food_image.id in dismissed_food_image_ids:
                continue

            food_names = [item.get("name", "?") for item in (food_image.detected_foods or [])]
            title = ", ".join(food_names[:3]) if food_names else "Scanned meal"
            if len(food_names) > 3:
                title += f" +{len(food_names) - 3} more"

            results.append({
                "source_type": "food_image",
                "source_id": food_image.id,
                "title": title,
                "calories": food_image.total_calories,
                "protein_g": food_image.total_protein_g,
                "carbs_g": food_image.total_carbs_g,
                "fat_g": food_image.total_fat_g,
                "created_at": food_image.uploaded_at,
            })

        results.sort(key=lambda r: r["created_at"], reverse=True)
        return results

    def dismiss_pending_confirmation(
        self,
        user_id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
    ) -> None:
        """
        Records a dismissal — after this, get_pending_confirmations()
        will never surface this specific recipe/scan again for
        this user. source_type is "recipe" or "food_image"
        (validated by the request schema's Literal type before
        this is ever called).
        """
        if source_type == "recipe":
            self.dismissal_repo.create(user_id=user_id, recipe_id=source_id)
        else:
            self.dismissal_repo.create(user_id=user_id, food_image_id=source_id)

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update_log(self, log_id: uuid.UUID, user_id: uuid.UUID, **fields) -> NutritionLog:
        """
        Updates a log entry, enforcing that only its owner
        may do so.

        Raises:
            NutritionLogNotFoundError: if no log exists with
                this id.
            NotLogOwnerError: if the log belongs to a
                different user.
        """
        log = self._get_owned_log_or_raise(log_id, user_id)
        return self.log_repo.update(log, **fields)

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete_log(self, log_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Deletes a log entry, enforcing the same ownership
        rule as update_log.
        """
        log = self._get_owned_log_or_raise(log_id, user_id)
        self.log_repo.delete(log)

    # ---------------------------------------------------
    # Internal Helper
    # ---------------------------------------------------

    def _get_owned_log_or_raise(self, log_id: uuid.UUID, user_id: uuid.UUID) -> NutritionLog:
        log = self.log_repo.get_by_id(log_id)

        if log is None:
            raise NutritionLogNotFoundError(f"No nutrition log found with id {log_id}.")

        if log.user_id != user_id:
            raise NotLogOwnerError("This log entry belongs to another user.")

        return log
