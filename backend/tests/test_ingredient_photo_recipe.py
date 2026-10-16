"""
=========================================================
AIMeals Backend
Manual Test — AIService Ingredient Photo -> Recipe Flow

Run as a module:
    python -m tests.test_ingredient_photo_recipe

Exercises the full two-step flow with REAL Claude API calls
(vision identification, then recipe generation) against the
live database. Uses the testuser@example.com fixture account.

IMPORTANT: Set IMAGE_PATH below to a real photo of raw
ingredients (vegetables, fruits, etc.) on your machine before
running.
=========================================================
"""

import mimetypes
from pathlib import Path

from app.B_database import SessionLocal
from app.models.user import User  # noqa  (relationship import gotcha)
from app.models.ai_interaction import AIInteraction  # noqa  (relationship import gotcha)
from app.models.recipe import Recipe  # noqa  (relationship import gotcha)
from app.repositories.user_repository import UserRepository
from app.services.ai_service import AIService
from app.core.exceptions import (
    AllergenDetectedError,
    ClaudeAPIError,
    IngredientIdentificationError,
    InsufficientCreditsError,
    RecipeGenerationError,
)

TEST_USER_EMAIL = "testuser@example.com"

# EDIT THIS to point at a real photo of raw ingredients on your machine.
IMAGE_PATH = r"D:\test_images\ingredients_photo.png"


def main():
    image_file = Path(IMAGE_PATH)
    if not image_file.exists():
        print(f"FAIL: IMAGE_PATH does not exist: {IMAGE_PATH}")
        print("Edit IMAGE_PATH at the top of this script to point at a real image file.")
        return

    media_type, _ = mimetypes.guess_type(str(image_file))
    if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        print(f"FAIL: unsupported or undetected image type: {media_type}")
        return

    image_bytes = image_file.read_bytes()
    print(f"Loaded image: {image_file.name} ({len(image_bytes)} bytes, {media_type})")

    db = SessionLocal()

    try:
        user_repo = UserRepository(db)
        ai_service = AIService(db)

        user = user_repo.get_by_email(TEST_USER_EMAIL)
        if user is None:
            print(f"FAIL: test user {TEST_USER_EMAIL} not found")
            return
        print(f"Using test user: {user.id}")

        # -----------------------------------------------
        # Step 1: identify_ingredients_from_image()
        # -----------------------------------------------
        try:
            scan = ai_service.identify_ingredients_from_image(
                user_id=user.id,
                image_bytes=image_bytes,
                media_type=media_type,
            )
        except InsufficientCreditsError as e:
            print(f"FAIL: insufficient credits for identification: {e}")
            return
        except ClaudeAPIError as e:
            print(f"FAIL: Claude API call failed during identification: {e}")
            return
        except IngredientIdentificationError as e:
            print(f"FAIL: could not parse identification response: {e}")
            return

        print(f"\nPASS: identify_ingredients_from_image() -> scan_id={scan.id}, status={scan.status}")
        print("Identified ingredients:")
        for item in scan.ingredients:
            note = f" ({item['confidence_note']})" if item.get("confidence_note") else ""
            print(f"  - {item['name']}{note}")

        # -----------------------------------------------
        # Step 2: generate_recipe_from_scan() — confirm
        # with NO corrections, exactly as identified.
        # -----------------------------------------------
        try:
            recipe = ai_service.generate_recipe_from_scan(
                scan_id=scan.id,
                user_id=user.id,
            )
        except InsufficientCreditsError as e:
            print(f"FAIL: insufficient credits for recipe generation: {e}")
            return
        except ClaudeAPIError as e:
            print(f"FAIL: Claude API call failed during recipe generation: {e}")
            return
        except RecipeGenerationError as e:
            print(f"FAIL: could not parse generated recipe: {e}")
            return
        except AllergenDetectedError as e:
            print(f"REJECTED (expected behavior if a real allergen risk exists): {e}")
            return

        print(f"\nPASS: generate_recipe_from_scan() -> recipe_id={recipe.id}")
        print(f"Title: {recipe.title}")
        print(f"Description: {recipe.description}")
        print(f"Servings: {recipe.servings}")
        print(f"Ingredients:\n{recipe.ingredients}")
        print(f"Instructions:\n{recipe.instructions}")

        print("\nFull ingredient-photo-to-recipe flow passed.")

    finally:
        db.close()


if __name__ == "__main__":
    main()