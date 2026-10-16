"""
=========================================================
AIMeals Backend
Manual Test — AIService Food Image Analysis (no disk storage,
one-item ambiguity clarification)

Run as a module:
    python -m tests.test_food_image_analysis

Exercises analyze_food_image() with a REAL Claude vision API
call against the live database. Uses the testuser@example.com
fixture account.

IMPORTANT: Set IMAGE_PATH below to a real photo of a prepared
food/dish (not raw ingredients) on your machine before running.
For best results testing the ambiguity flow, use a photo where
the protein is genuinely uncertain (e.g. the scrambled-egg
stir-fry photo that originally caused the chicken/egg bug).
=========================================================
"""

import mimetypes
from pathlib import Path

from app.B_database import SessionLocal
from app.models.user import User  # noqa  (relationship import gotcha)
from app.models.ai_interaction import AIInteraction  # noqa  (relationship import gotcha)
from app.models.recipe import Recipe  # noqa  (relationship import gotcha)
from app.models.food_image import FoodImageStatus
from app.repositories.user_repository import UserRepository
from app.services.ai_service import AIService
from app.core.exceptions import (
    ClaudeAPIError,
    FoodImageAnalysisError,
    InappropriateImageError,
    InsufficientCreditsError,
    UploadTooLargeError,
)

TEST_USER_EMAIL = "testuser@example.com"

# EDIT THIS to point at a real photo of a prepared food/dish on your machine.
IMAGE_PATH = r"D:\test_images\test_photo.png"


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
        # analyze_food_image()
        # -----------------------------------------------
        try:
            food_image = ai_service.analyze_food_image(
                user_id=user.id,
                image_bytes=image_bytes,
                media_type=media_type,
                original_filename=image_file.name,
            )
        except UploadTooLargeError as e:
            print(f"FAIL: image too large: {e}")
            return
        except InsufficientCreditsError as e:
            print(f"FAIL: insufficient credits: {e}")
            return
        except ClaudeAPIError as e:
            print(f"FAIL: Claude API call failed: {e}")
            return
        except InappropriateImageError as e:
            print(f"REJECTED (expected behavior if the image wasn't food): {e}")
            return
        except FoodImageAnalysisError as e:
            print(f"FAIL: could not parse analysis response: {e}")
            return

        print(f"\nPASS: analyze_food_image() -> food_image_id={food_image.id}")
        print(f"Status: {food_image.status}")
        print(f"image_url (should always be None now): {food_image.image_url}")
        print(f"Identified food: {food_image.identified_food_name}")
        print(f"Estimated calories: {food_image.estimated_calories}")
        print(f"Estimated protein (g): {food_image.estimated_protein_g}")
        print(f"Estimated carbs (g): {food_image.estimated_carbs_g}")
        print(f"Estimated fat (g): {food_image.estimated_fat_g}")

        if food_image.image_url is not None:
            print("\nWARNING: image_url is not None — an image may have been saved to disk unexpectedly.")

        # -----------------------------------------------
        # If PENDING, walk through resolving the ambiguity
        # -----------------------------------------------
        if food_image.status == FoodImageStatus.PENDING:
            ambiguity = food_image.ambiguity
            if ambiguity is None:
                print("\nWARNING: status is PENDING but ambiguity is None — this shouldn't happen.")
                return

            print(f"\nAmbiguity flagged: {ambiguity['question']}")
            options = ambiguity["options"]
            for opt in options:
                print(
                    f"  - {opt['label']}: {opt['identified_food_name']} "
                    f"({opt['estimated_calories']} kcal)"
                )

            chosen_label = options[0]["label"]
            print(f"\nResolving with choice: '{chosen_label}' (picking the first option for this test)")

            resolved = ai_service.resolve_food_image_ambiguity(
                image_id=food_image.id,
                user_id=user.id,
                chosen_option_label=chosen_label,
            )

            print(f"\nPASS: resolve_food_image_ambiguity() -> status={resolved.status}")
            print(f"Final identified food: {resolved.identified_food_name}")
            print(f"Final estimated calories: {resolved.estimated_calories}")
            print(f"ambiguity field cleared: {resolved.ambiguity is None}")
        else:
            print("\nNo ambiguity flagged — analysis was confident and went straight to CONFIRMED.")

        print("\nFood image analysis flow passed.")

    finally:
        db.close()


if __name__ == "__main__":
    main()