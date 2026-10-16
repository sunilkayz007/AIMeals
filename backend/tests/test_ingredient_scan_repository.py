"""
=========================================================
AIMeals Backend
Manual Test — IngredientScanRepository

Run as a module:
    python -m tests.test_ingredient_scan_repository

Exercises create / get_by_id / update / get_expired / delete
against the live database. Uses the testuser@example.com
fixture account.
=========================================================
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.B_database import SessionLocal
from app.models.ingredient_scan import IngredientScanStatus
from app.models.user import User  # noqa  (relationship import gotcha)
from app.models.ai_interaction import AIInteraction  # noqa  (relationship import gotcha)
from app.models.recipe import Recipe  # noqa  (relationship import gotcha)
from app.repositories.ingredient_scan_repository import IngredientScanRepository
from app.repositories.user_repository import UserRepository

TEST_USER_EMAIL = "testuser@example.com"


def main():
    db = SessionLocal()

    try:
        user_repo = UserRepository(db)
        scan_repo = IngredientScanRepository(db)

        # -----------------------------------------------
        # Setup: fetch test user
        # -----------------------------------------------
        user = user_repo.get_by_email(TEST_USER_EMAIL)
        if user is None:
            print(f"FAIL: test user {TEST_USER_EMAIL} not found")
            return
        print(f"Using test user: {user.id}")

        # -----------------------------------------------
        # 1. create()
        # -----------------------------------------------
        initial_ingredients = [
            {"name": "Tomato", "confidence_note": None},
            {"name": "Onion", "confidence_note": None},
            {"name": "Zucchini", "confidence_note": "could be cucumber"},
        ]
        scan = scan_repo.create(user_id=user.id, ingredients=initial_ingredients)
        assert scan.status == IngredientScanStatus.PENDING
        assert len(scan.ingredients) == 3
        print(f"PASS: create() -> scan_id={scan.id}, status={scan.status}")

        # -----------------------------------------------
        # 2. get_by_id()
        # -----------------------------------------------
        fetched = scan_repo.get_by_id(scan.id)
        if fetched is None:
            print("FAIL: get_by_id() returned None")
            return
        assert fetched.id == scan.id
        print("PASS: get_by_id()")

        # -----------------------------------------------
        # 3. update() — simulate a user correction
        #    (Zucchini -> Cucumber) + confirm
        # -----------------------------------------------
        corrected_ingredients = [
            {"name": "Tomato", "confidence_note": None},
            {"name": "Onion", "confidence_note": None},
            {"name": "Cucumber", "confidence_note": None},
        ]
        updated = scan_repo.update(
            scan,
            ingredients=corrected_ingredients,
            status=IngredientScanStatus.CONFIRMED,
        )
        assert updated.status == IngredientScanStatus.CONFIRMED
        assert updated.ingredients[2]["name"] == "Cucumber"
        print("PASS: update()")

        # -----------------------------------------------
        # 4. get_expired() — create a second scan, manually
        #    backdate it, confirm it's picked up. The
        #    CONFIRMED scan from step 3 is recent (not
        #    backdated), so it correctly does NOT show up —
        #    not because of its status, but because it isn't
        #    old enough yet. get_expired() sweeps ANY status
        #    once 24h has passed (confirmed scans included,
        #    per project decision).
        # -----------------------------------------------
        stale_scan = scan_repo.create(
            user_id=user.id,
            ingredients=[{"name": "Carrot", "confidence_note": None}],
        )
        stale_scan.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        db.commit()

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        expired = scan_repo.get_expired(cutoff_time=cutoff)
        expired_ids = {s.id for s in expired}

        assert stale_scan.id in expired_ids, "backdated scan should be expired"
        assert scan.id not in expired_ids, "recent scan should not be expired yet"
        print(f"PASS: get_expired() -> found {len(expired)} expired scan(s)")

        # -----------------------------------------------
        # 5. delete()
        # -----------------------------------------------
        scan_repo.delete(scan)
        scan_repo.delete(stale_scan)

        should_be_gone = scan_repo.get_by_id(scan.id)
        assert should_be_gone is None
        print("PASS: delete()")

        print("\nAll IngredientScanRepository tests passed.")

    finally:
        db.close()


if __name__ == "__main__":
    main()